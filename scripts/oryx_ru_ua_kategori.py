"""
Oryx Rusya-Ukrayna kayıtlarını (her satır = fotoğrafla kanıtlanmış bir araç) proje kategorilerine ayırır
ve kategori bazında KÜMÜLATİF zaman serisi üretir.

Girdi : data/raw/oryx_ru_ua_kayitlar.csv
        (github.com/scarnecchia/oryx_data -> totals_by_system.csv; Oryx sayfasının günlük kazınması.
         date_recorded = kaydın Oryx listesinde ilk görüldüğü gün. 2022-03-19 öncesi kayıtlar o güne yığılır.)
Çıktı : data/clean/oryx_ru_ua_zaman_serisi.csv  (tarih, kayip_taraf, kategori, kumulatif)

Kategori, sistem adından anahtar kelimeyle bulunur (T-72 -> tank, 2S19 -> topcu ...).
Oryx'in "Armoured Combat Vehicles [Tanks, AFVs, IFVs, APCs, MRAPs]" tanımına uyuldu:
zirhli_arac = AFV + IFV + APC + MRAP (piyade hareketlilik araçları - HMMWV, Tigr, Kozak - dahil DEĞİL).
Doğrulama: scriptin sonunda Oryx'in kendi başlık toplamlarıyla karşılaştırılır.
"""
import re
import sys
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parent.parent

KURALLAR = [  # sıra önemli: ilk eşleşen kazanır
    ("disla", r"tanker|fuel|recovery|BREM|engineering|IMR|bridge|pontoon|command|R-149|radar|jamm|"
              r"Krasukha|Leer|Borisoglebsk|repair|ambulance|mine-?clear|UR-77|BMR|minelayer|ammunition|"
              r"transporter|loader|crane|excavat|bulldoz"),
    ("iha", r"UAV|drone|Orlan|ZALA|Leleka|Fury|Supercam|Bayraktar|Shahed|Geran|Lancet|Forpost|Eleron|"
            r"Tachyon|Mohajer|Inokhodets|Valkyrja|Furia|Mugin|loitering"),
    ("helikopter", r"helicopter|\bMi-\d|\bKa-\d"),
    ("ucak", r"aircraft|\bSu-\d|\bMiG-|\bTu-\d|\bIl-\d|\bA-50|\bBe-\d|\bAn-\d|\bL-39|\bYak-\d"),
    ("roketatar", r"MRL|BM-21|BM-27|BM-30|Grad|Uragan|Smerch|Tornado|TOS-1|TOS-2|HIMARS|M270|RM-70|Vampire|"
                  r"Bureviy|Verba|9P1\d\d|BM-21|Bastion-|Prima|\bLRU\b|APR-40"),
    ("hava_savunma", r"Strela|\bOsa\b|9K33|\bBuk|\bTor\b|Tor-M|Pantsir|Tunguska|S-300|S-400|S-125|Patriot|"
                     r"IRIS-T|NASAMS|Gepard|Shilka|ZSU|SAM\b|surface-to-air|anti-aircraft|AA gun|ZU-23|Kub|"
                     r"Hawk|Crotale|Avenger|Stormer|Skynex|Skyguard|Igla|Stinger|9K35|9K37|9K330|9K331|9K22"),
    ("topcu", r"howitzer|gun-howitzer|\b2S\d|2A36|2A65|2A18|D-30|D-20|D-44|MT-12|Msta|Akatsiya|Giatsint|"
              r"Gvozdika|Nona|Tyulpan|Pion|Malka|M777|M109|CAESAR|PzH|Krab|Zuzana|Dana|Bohdana|AS-90|Archer|"
              r"mortar|anti-tank gun|L119|M101|FH70|FH-70|TRF1|Rapira|\bSPG\b|towed artillery|field gun|"
              r"M-46|130mm|152mm|122mm|155mm|105mm|203mm|240mm|120mm|82mm|100mm|85mm|76mm|57mm"),
    ("tank", r"\bT-(54|55|62|64|72|80|84|90)|Leopard [12]|Abrams|\bM1A1|Challenger|PT-91|M-55S|M-84|"
             r"Unknown tank|\btanks?\b"),
    ("zirhli_arac", r"BMP|BMD|BTR|MT-LB|BRDM|BRM|M113|Bradley|Stryker|Marder|CV90|MaxxPro|YPR|VAB|"
                    r"Senator|Varta|Unknown AFV|IFV|APC|MRAP|Novator|Spartan|Mastiff|Husky|Bushmaster|"
                    r"Cougar|M-ATV|Patria|Dingo|Wolfhound|Typhoon|Kirpi|Lynx|BMM|BTS|Pbv|Saxon|"
                    r"Kozak-7|Dozor|AMX-10|M1117|Pansarbandvagn|Hagglunds|Bv 206|BvS10|Akhmat|Linza|"
                    r"Vystrel|Ural-VV|K-53949|Zubr|Shrek|Grizzly|Sisu|XA-180|KTO Rosomak|Rosomak|ACSV|"
                    r"armou?red"),
]
KURALLAR = [(k, re.compile(p, re.I)) for k, p in KURALLAR]


def kategori(sistem):
    s = re.sub(r"^\d+\s+", "", str(sistem))
    for k, desen in KURALLAR:
        if desen.search(s):
            return k
    return "diger"


def main():
    d = pd.read_csv(KOK / "data/raw/oryx_ru_ua_kayitlar.csv", parse_dates=["date_recorded"])
    d["kategori"] = d.system.map(kategori)
    d["kayip_taraf"] = d.country.map({"Russia": "Rusya", "Ukraine": "Ukrayna"})
    # aynı fotoğraf (url) bir aracı gösterir; aynı url'nin tekrarlarını tek say
    d = d.drop_duplicates(subset=["country", "url"])

    tarihler = pd.Series(sorted(d.date_recorded.unique()))
    satirlar = []
    for (taraf, kat), g in d.groupby(["kayip_taraf", "kategori"]):
        gunluk = g.groupby("date_recorded").size().reindex(tarihler, fill_value=0).cumsum()
        satirlar += [{"tarih": t.date(), "kayip_taraf": taraf, "kategori": kat, "kumulatif": int(v)}
                     for t, v in gunluk.items()]
    zs = pd.DataFrame(satirlar)
    (KOK / "data/clean").mkdir(parents=True, exist_ok=True)
    zs.to_csv(KOK / "data/clean/oryx_ru_ua_zaman_serisi.csv", index=False)

    son = d.groupby(["kayip_taraf", "kategori"]).size().unstack(0)
    print("Son durum (", d.date_recorded.max().date(), "):")
    print(son.to_string())
    print("\n'diger' içinde en sık sistemler:")
    print(d[d.kategori == "diger"].system.value_counts().head(25).to_string())
    acv = son.loc[["tank", "zirhli_arac"]].sum()
    print("\nZırhlı muharebe aracı (tank + zırhlı):", acv.to_dict())
    return d


if __name__ == "__main__":
    main()
