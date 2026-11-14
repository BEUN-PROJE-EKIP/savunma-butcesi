"""
GDELT DOC 2.0 API'den 2020 Karabağ savaşı medya verisini çeker.
"Kalabalık" = dünya medyası. Bu script iki şey toplar:

  1) Makale listesi (ArtList): her makalenin URL'si, başlığı, alan adı, dili, ülkesi, görülme zamanı.
     API tek istekte en fazla 250 makale döndürdüğü için dönem küçük pencerelere bölünür;
     bir pencere 250'yi doldurursa otomatik olarak ikiye bölünür (en küçük pencere 1 saat).
  2) Zaman serileri: günlük haber hacmi (TimelineVolRaw) ve ortalama ton (TimelineTone).

Kullanım (proje kökünden, kendi bilgisayarında - internet gerekir):
    pip install requests pandas
    python scripts/gdelt_doc_cek.py                 # tüm dönem (27 Eyl - 15 Kas 2020)
    python scripts/gdelt_doc_cek.py --test          # sadece 1 günü dener, API'nin 2020'yi verdiğini doğrular
    python scripts/gdelt_doc_cek.py --bas 2020-10-01 --bit 2020-10-07

Çıktılar (data/raw/gdelt/):
    doc_makaleler.csv   : url, baslik, domain, dil, ulke, gorulme_zamani, sorgu
    doc_hacim.csv       : tarih, sorgu, makale_sayisi, toplam_makale, oran
    doc_ton.csv         : tarih, sorgu, ortalama_ton

Notlar:
- GDELT saniyede 1'den fazla isteği engeller; script her istek arasında BEKLE saniye bekler.
  Tüm dönem ~ 1 saat sürebilir. Yarıda kesilirse tekrar çalıştır: biten pencereler
  data/raw/gdelt/_ilerleme.json'da tutulur ve atlanır.
- Sorgu, GDELT'in makine çevirisi üzerinden 65 dilde arar; başlıklar ise orijinal dildedir.
- Başlıktan sayı çıkarmak için ayrıca:  python scripts/medya_sayi_cikar.py
"""
import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

API = "https://api.gdeltproject.org/api/v2/doc/doc"
KOK = Path(__file__).resolve().parent.parent
CIKTI = KOK / "data" / "raw" / "gdelt"
BEKLE = 6  # saniye; GDELT 5 sn'de 1 istek ister
BASLIK = {"User-Agent": "karabag-ders-projesi/1.0 (universite odevi)"}

# Ana sorgu: savaşla ilgili tüm haberler.
# Kayıp sorgusu: sayı içeren kayıp haberlerini yakalamak için daraltılmış sorgu
# (ana sorgunun 250 sınırına takılıp kayıp haberlerini kaçırmamak için ayrı çekilir).
SORGULAR = {
    "genel": '(karabakh OR artsakh OR "nagorno-karabakh")',
    "kayip": '(karabakh OR artsakh) (destroyed OR killed OR casualties OR "shot down" OR tanks OR drones)',
}

VARSAYILAN_BAS = "2020-09-27"
VARSAYILAN_BIT = "2020-11-15"
MAX_KAYIT = 250
EN_KUCUK_PENCERE = timedelta(hours=1)


def gdelt_zaman(t):
    return t.strftime("%Y%m%d%H%M%S")


def istek(params, deneme=4):
    """GDELT'e istek atar; JSON döndürür. Hata/limit durumunda bekleyip tekrar dener."""
    for i in range(deneme):
        try:
            r = requests.get(API, params=params, timeout=60, headers=BASLIK)
            time.sleep(BEKLE)
            if r.status_code == 429 or "limit requests" in r.text[:300].lower():
                bekle = 30 * 2 ** i   # 30, 60, 120, 240 sn
                print(f"  hız sınırı (HTTP {r.status_code}): {r.text[:200].strip()!r}")
                print(f"  {bekle} sn bekleniyor...")
                time.sleep(bekle)
                continue
            r.raise_for_status()
            metin = r.text.strip()
            if not metin:
                return {}
            try:
                return json.loads(metin)
            except json.JSONDecodeError:
                # GDELT hatalı sorguda düz metin hata döndürür
                print(f"  GDELT JSON yerine metin döndürdü: {metin[:200]}")
                return {}
        except requests.RequestException as e:
            print(f"  istek hatası ({e}), {10 * (i + 1)} sn sonra tekrar...")
            time.sleep(10 * (i + 1))
    print("  !! istek başarısız, pencere atlanıyor")
    return None


def makaleleri_cek(sorgu_adi, sorgu, bas, bit, ilerleme, kayitlar):
    anahtar = f"{sorgu_adi}|{gdelt_zaman(bas)}|{gdelt_zaman(bit)}"
    if anahtar in ilerleme:
        return
    params = {
        "query": sorgu,
        "mode": "ArtList",
        "maxrecords": MAX_KAYIT,
        "format": "json",
        "sort": "DateAsc",
        "startdatetime": gdelt_zaman(bas),
        "enddatetime": gdelt_zaman(bit),
    }
    veri = istek(params)
    if veri is None:
        return
    makaleler = veri.get("articles", [])
    print(f"  {sorgu_adi:6} {bas:%Y-%m-%d %H:%M} -> {bit:%m-%d %H:%M}: {len(makaleler)} makale")

    if len(makaleler) >= MAX_KAYIT and (bit - bas) > EN_KUCUK_PENCERE:
        orta = bas + (bit - bas) / 2
        makaleleri_cek(sorgu_adi, sorgu, bas, orta, ilerleme, kayitlar)
        makaleleri_cek(sorgu_adi, sorgu, orta, bit, ilerleme, kayitlar)
        ilerleme.add(anahtar)
        return

    for m in makaleler:
        kayitlar.append({
            "url": m.get("url"),
            "baslik": m.get("title"),
            "domain": m.get("domain"),
            "dil": m.get("language"),
            "ulke": m.get("sourcecountry"),
            "gorulme_zamani": m.get("seendate"),
            "sorgu": sorgu_adi,
        })
    ilerleme.add(anahtar)


def zaman_serisi(sorgu_adi, sorgu, bas, bit, mod):
    params = {
        "query": sorgu,
        "mode": mod,
        "format": "json",
        "timelinesmooth": 0,
        "startdatetime": gdelt_zaman(bas),
        "enddatetime": gdelt_zaman(bit),
    }
    veri = istek(params) or {}
    satirlar = []
    for seri in veri.get("timeline", []):
        for nokta in seri.get("data", []):
            satirlar.append({
                "tarih": nokta.get("date"),
                "sorgu": sorgu_adi,
                "seri": seri.get("series"),
                "deger": nokta.get("value"),
                "toplam": nokta.get("norm"),
            })
    return satirlar


def kaydet_makaleler(kayitlar, ilerleme):
    yol = CIKTI / "doc_makaleler.csv"
    df = pd.DataFrame(kayitlar)
    if yol.exists():
        df = pd.concat([pd.read_csv(yol), df], ignore_index=True)
    if not df.empty:
        df = df.drop_duplicates(subset=["url", "sorgu"])
        df.to_csv(yol, index=False, encoding="utf-8")
    (CIKTI / "_ilerleme.json").write_text(json.dumps(sorted(ilerleme)), encoding="utf-8")
    return len(df)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bas", default=VARSAYILAN_BAS)
    ap.add_argument("--bit", default=VARSAYILAN_BIT)
    ap.add_argument("--test", action="store_true", help="sadece 10 Ekim 2020'yi dener")
    ap.add_argument("--sadece-zaman", action="store_true", help="makale listesini atla")
    a = ap.parse_args()

    CIKTI.mkdir(parents=True, exist_ok=True)

    if a.test:
        params = {"query": SORGULAR["genel"], "mode": "ArtList", "maxrecords": 5, "format": "json",
                  "startdatetime": "20201010000000", "enddatetime": "20201011000000"}
        veri = istek(params)
        arts = (veri or {}).get("articles", [])
        if not arts:
            print("API 2020 için makale döndürmedi. Yanıt:", veri)
            print("-> GKG/BigQuery yolunu kullan: scripts/gdelt_gkg_bigquery.sql")
            sys.exit(1)
        for m in arts:
            print(m.get("seendate"), m.get("domain"), "|", m.get("title"))
        print("OK: API 2020 verisi veriyor.")
        return

    bas = datetime.fromisoformat(a.bas)
    bit = datetime.fromisoformat(a.bit)

    # 1) Zaman serileri (her sorgu için tek istek yeter)
    print("Zaman serileri çekiliyor...")
    hacim, ton = [], []
    for ad, s in SORGULAR.items():
        hacim += zaman_serisi(ad, s, bas, bit, "TimelineVolRaw")
        ton += zaman_serisi(ad, s, bas, bit, "TimelineTone")
    if hacim:
        h = pd.DataFrame(hacim).rename(columns={"deger": "makale_sayisi", "toplam": "toplam_makale"})
        h["oran"] = h["makale_sayisi"] / h["toplam_makale"]
        h.drop(columns="seri").to_csv(CIKTI / "doc_hacim.csv", index=False, encoding="utf-8")
    if ton:
        pd.DataFrame(ton).rename(columns={"deger": "ortalama_ton"}) \
            .drop(columns=["seri", "toplam"]).to_csv(CIKTI / "doc_ton.csv", index=False, encoding="utf-8")
    print(f"  hacim: {len(hacim)} nokta, ton: {len(ton)} nokta")

    if a.sadece_zaman:
        return

    # 2) Makale listesi, gün gün (doluysa otomatik bölünür)
    ilerleme_yolu = CIKTI / "_ilerleme.json"
    ilerleme = set(json.loads(ilerleme_yolu.read_text(encoding="utf-8"))) if ilerleme_yolu.exists() else set()
    gun = bas
    while gun < bit:
        sonraki = min(gun + timedelta(days=1), bit)
        kayitlar = []
        for ad, s in SORGULAR.items():
            makaleleri_cek(ad, s, gun, sonraki, ilerleme, kayitlar)
        toplam = kaydet_makaleler(kayitlar, ilerleme)  # her gün sonunda kaydet
        print(f"{gun:%Y-%m-%d} bitti, dosyada toplam {toplam} makale")
        gun = sonraki

    print("Bitti. Şimdi: python scripts/medya_sayi_cikar.py")


if __name__ == "__main__":
    main()
