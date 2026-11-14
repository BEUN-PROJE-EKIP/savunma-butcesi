"""
Oryx 2020 Karabağ kayıp listesini kazıyıp CSV'ye döker.

Kullanım:
    python scrape_oryx.py                      # canlı sayfayı indirir
    python scrape_oryx.py --html sayfa.html    # kaydedilmiş bir HTML'den okur
    python scrape_oryx.py --url <wayback_linki> --out ../data/raw/oryx_2020-10-15.csv

Çıktı sütunları:
    taraf | kategori | model | sira_no | durum | kanit_linki
"""
import argparse
import re
import sys

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://www.oryxspioenkop.com/2020/09/the-fight-for-nagorno-karabakh.html"

# Oryx'in İngilizce kategori adları -> projenin ortak kategori sözlüğü
KATEGORI_ESLEME = {
    "tanks": "tank",
    "armoured fighting vehicles": "zirhli_arac",
    "infantry fighting vehicles": "zirhli_arac",
    "armoured personnel carriers": "zirhli_arac",
    "infantry mobility vehicles": "zirhli_arac",
    "towed artillery": "topcu",
    "self-propelled artillery": "topcu",
    "multiple rocket launchers": "roketatar",
    "surface-to-air missile systems": "hava_savunma",
    "self-propelled anti-aircraft guns": "hava_savunma",
    "anti-aircraft guns": "hava_savunma",
    "radars": "radar",
    "jammers and deception systems": "elektronik_harp",
    "aircraft": "hava_araci",
    "helicopters": "hava_araci",
    "unmanned aerial vehicles": "iha",
    "trucks, vehicles and jeeps": "lojistik",
    "mortars": "topcu",
}

DURUMLAR = ("destroyed", "damaged", "abandoned", "captured")


def kategori_bul(baslik):
    b = re.sub(r"\(.*", "", baslik).strip().lower()
    return KATEGORI_ESLEME.get(b, b.replace(" ", "_"))


def ayristir(html):
    soup = BeautifulSoup(html, "lxml")
    govde = soup.select_one(".post-body") or soup
    satirlar = []
    taraf = None
    for el in govde.find_all(["h3", "li"]):
        metin = el.get_text(" ", strip=True)
        if el.name == "h3":
            if metin.lower().startswith("armenia"):
                taraf = "Ermenistan"
            elif metin.lower().startswith("azerbaijan"):
                taraf = "Azerbaycan"
            continue
        if taraf is None:
            continue
        # Kategori satırı: "Tanks (224, of which destroyed: ...)" ve içinde kayıt linki yoksa
        linkler = el.find_all("a")
        if not linkler:
            continue
        # Kategori başlığı genelde ul'dan önceki <h3> veya kalın satırdır; modelin kendisinden önceki
        # en yakın kategori başlığını bulmak için önceki kardeşlere bakılır
        model = re.split(r":", metin, maxsplit=1)[0]
        model = re.sub(r"^\d+\s+", "", model).strip()
        kat_el = el.find_previous(lambda t: t.name in ("h3", "li", "p") and t is not el
                                  and not t.find("a") and re.search(r"\(\d+", t.get_text()))
        kategori = kategori_bul(kat_el.get_text(" ", strip=True)) if kat_el else "bilinmiyor"
        for a in linkler:
            t = a.get_text(" ", strip=True).lower()
            m = re.match(r"\(?\s*(\d+)\s*,\s*([a-z ,]+?)\s*\)?$", t)
            if not m:
                continue
            durum = next((d for d in DURUMLAR if d in m.group(2)), m.group(2))
            satirlar.append({
                "taraf": taraf,
                "kategori": kategori,
                "model": model,
                "sira_no": int(m.group(1)),
                "durum": durum,
                "kanit_linki": a.get("href"),
            })
    return pd.DataFrame(satirlar)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=URL)
    p.add_argument("--html", help="Önceden kaydedilmiş HTML dosyası")
    p.add_argument("--out", default="../data/raw/oryx_karabag.csv")
    a = p.parse_args()

    if a.html:
        html = open(a.html, encoding="utf-8").read()
    else:
        r = requests.get(a.url, timeout=60, headers={"User-Agent": "karabag-proje/0.1"})
        r.raise_for_status()
        html = r.text

    df = ayristir(html)
    if df.empty:
        sys.exit("Hiç kayıt bulunamadı: sayfa yapısı değişmiş olabilir.")
    df.to_csv(a.out, index=False, encoding="utf-8-sig")
    print(f"{len(df)} kayıt yazıldı -> {a.out}")
    print(df.groupby(["taraf", "kategori"]).size().to_string())


if __name__ == "__main__":
    main()
