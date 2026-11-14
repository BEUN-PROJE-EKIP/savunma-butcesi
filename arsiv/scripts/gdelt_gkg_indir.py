"""
GDELT GKG 2.0 ham dosyalarından 2020 Karabağ haberlerindeki SAYILARI çıkarır.
(DOC API IP'ye 429 "hız sınırı" verdiği için bu yol kullanılıyor; ham dosya sunucusunda sınır yok.)

GDELT her 15 dakikada bir GKG dosyası yayınlar (~7,5 MB zip). Script her dosyayı indirir,
içinden Karabağ'la ilgili makaleleri süzer, makalelerdeki sayı-nesne çiftlerini
(Amounts: "30,Armenian tanks" / V2Counts: "KILL#40#soldiers") çıkarır ve dosyayı bellekten atar.
Diske sadece süzülmüş sonuç yazılır.

Kullanım (proje kökünden):
    python scripts/gdelt_gkg_indir.py                # her saatten 1 dosya (~%25 örneklem, ~1.200 dosya, ~9 GB indirme)
    python scripts/gdelt_gkg_indir.py --adim 1       # tüm dosyalar (~4.700 dosya, ~35 GB) - sadece hızlı internette
    python scripts/gdelt_gkg_indir.py --ceviri       # İngilizce dışı (çevrilmiş) haberleri de ekle (~+%40 indirme)
    python scripts/gdelt_gkg_indir.py --test         # tek dosyayı dener

Yarıda kesilirse tekrar çalıştır: biten dosyalar data/raw/gdelt/_gkg_ilerleme.txt'de tutulur ve atlanır.

Çıktılar (data/raw/gdelt/):
    gkg_sayilar.csv : tarih_saat, domain, url, kaynak_dil, ton, kaynak_alan, adet, nesne, konum
                      (BigQuery sorgusuyla aynı format -> medya_sayi_cikar.py doğrudan okur)
    gkg_makaleler.csv : her Karabağ makalesi için bir satır (tarih_saat, domain, url, kaynak_dil, ton)
                        -> günlük haber hacmi ve ton için
"""
import argparse
import csv
import io
import re
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import requests

csv.field_size_limit(10**9)

KOK = Path(__file__).resolve().parent.parent
CIKTI = KOK / "data" / "raw" / "gdelt"
TABAN = "http://data.gdeltproject.org/gdeltv2/"

KARABAG = re.compile(r"karabakh|qarabag|artsakh|stepanakert|xankendi|khankendi|shusha|\bsusa\b", re.I)
KARABAG_URL = re.compile(r"karabakh|karabag|qarabag|artsakh", re.I)
ILGILI_NESNE = re.compile(
    r"tank|armou?red|vehicle|artillery|howitzer|mortar|launcher|grad|smerch|drone|uav|bayraktar|harop|"
    r"helicopter|aircraft|plane|jet|su-25|air defen|s-300|osa|radar|truck|soldier|servicem|troop|militar|"
    r"fighter|personnel|casualt|dead|killed|wounded|civilian", re.I)

SAYI_SUTUN = ["tarih_saat", "domain", "url", "kaynak_dil", "ton", "kaynak_alan", "adet", "nesne", "konum"]
MAKALE_SUTUN = ["tarih_saat", "domain", "url", "kaynak_dil", "ton"]

# GKG 2.0 sütun sırası
DATE, DOMAIN, URL, V2COUNTS, V2LOC, V2TONE, AMOUNTS, TRANS = 1, 3, 4, 6, 10, 15, 24, 25


def dosya_adlari(bas, bit, adim, ceviri):
    t = bas
    while t < bit:
        damga = t.strftime("%Y%m%d%H%M%S")
        yield f"{damga}.gkg.csv.zip"
        if ceviri:
            yield f"{damga}.translation.gkg.csv.zip"
        t += timedelta(minutes=15 * adim)


def satiri_isle(alanlar):
    """Bir GKG satırı Karabağ'la ilgiliyse (makale_satiri, [sayi_satirlari]) döndürür."""
    if len(alanlar) < 26:
        return None
    if not (KARABAG.search(alanlar[V2LOC]) or KARABAG_URL.search(alanlar[URL])):
        return None
    dil_m = re.search(r"srclc:(\w+)", alanlar[TRANS])
    dil = dil_m.group(1) if dil_m else "eng"
    try:
        ton = float(alanlar[V2TONE].split(",")[0])
    except ValueError:
        ton = None
    ortak = [alanlar[DATE], alanlar[DOMAIN], alanlar[URL], dil, ton]

    sayilar = []
    for parca in alanlar[AMOUNTS].split(";"):
        p = parca.split(",")
        if len(p) >= 3 and ILGILI_NESNE.search(p[1]):
            try:
                adet = float(p[0])
            except ValueError:
                continue
            if 1 <= adet <= 100000:
                sayilar.append(ortak + ["amount", adet, p[1].lower(), p[-1]])
    for parca in alanlar[V2COUNTS].split(";"):
        p = parca.split("#")
        if len(p) >= 3 and p[0] in ("KILL", "WOUND", "SEIZE") and ILGILI_NESNE.search(p[2] or "killed"):
            try:
                adet = float(p[1])
            except ValueError:
                continue
            if 1 <= adet <= 100000:
                sayilar.append(ortak + ["count_" + p[0], adet, p[2].lower(), p[-1]])
    return ortak, sayilar


def dosyayi_isle(ad, oturum):
    for deneme in range(4):
        try:
            r = oturum.get(TABAN + ad, timeout=120)
            if r.status_code == 404:
                return ad, [], [], "yok"
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if deneme == 3:
                return ad, None, None, f"hata: {e}"
            time.sleep(5 * (deneme + 1))
    makaleler, sayilar = [], []
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        with z.open(z.namelist()[0]) as f:
            for satir in io.TextIOWrapper(f, encoding="utf-8", errors="replace"):
                if not KARABAG.search(satir):      # hızlı ön eleme
                    continue
                sonuc = satiri_isle(satir.rstrip("\n").split("\t"))
                if sonuc:
                    makaleler.append(sonuc[0])
                    sayilar.extend(sonuc[1])
    return ad, makaleler, sayilar, "ok"


def ekle(yol, sutunlar, satirlar):
    yeni = not yol.exists()
    with open(yol, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if yeni:
            w.writerow(sutunlar)
        w.writerows(satirlar)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bas", default="2020-09-27")
    ap.add_argument("--bit", default="2020-11-15")
    ap.add_argument("--adim", type=int, default=4, help="kaç 15-dk dosyada bir alınsın (4 = saatte 1)")
    ap.add_argument("--ceviri", action="store_true", help="İngilizce dışı haberleri de al")
    ap.add_argument("--paralel", type=int, default=4)
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()

    CIKTI.mkdir(parents=True, exist_ok=True)
    oturum = requests.Session()
    oturum.headers["User-Agent"] = "karabag-ders-projesi/1.0"

    if a.test:
        ad, mak, say, durum = dosyayi_isle("20201015120000.gkg.csv.zip", oturum)
        print(durum, f"{len(mak)} Karabağ makalesi, {len(say)} sayı")
        for s in say[:10]:
            print("  ", s[1], "|", s[6], s[7])
        return

    ilerleme_yolu = CIKTI / "_gkg_ilerleme.txt"
    biten = set(ilerleme_yolu.read_text().split()) if ilerleme_yolu.exists() else set()
    adlar = [d for d in dosya_adlari(datetime.fromisoformat(a.bas), datetime.fromisoformat(a.bit),
                                     a.adim, a.ceviri) if d not in biten]
    print(f"{len(adlar)} dosya indirilecek ({len(biten)} tanesi daha önce bitmiş)")

    t0, toplam_mak, toplam_say = time.time(), 0, 0
    with ThreadPoolExecutor(a.paralel) as havuz, open(ilerleme_yolu, "a") as ilerleme:
        isler = [havuz.submit(dosyayi_isle, ad, oturum) for ad in adlar]
        for i, is_ in enumerate(as_completed(isler), 1):
            ad, mak, say, durum = is_.result()
            if mak is None:
                print(f"  !! {ad} {durum} (sonra tekrar çalıştırınca denenecek)")
                continue
            ekle(CIKTI / "gkg_makaleler.csv", MAKALE_SUTUN, mak)
            ekle(CIKTI / "gkg_sayilar.csv", SAYI_SUTUN, say)
            ilerleme.write(ad + "\n"); ilerleme.flush()
            toplam_mak += len(mak); toplam_say += len(say)
            if i % 20 == 0 or i == len(isler):
                gecen = time.time() - t0
                kalan = gecen / i * (len(isler) - i)
                print(f"{i}/{len(isler)}  {toplam_mak} makale, {toplam_say} sayı  "
                      f"(kalan ~{kalan/60:.0f} dk)")
    print("Bitti. Şimdi: python scripts/medya_sayi_cikar.py")


if __name__ == "__main__":
    main()
