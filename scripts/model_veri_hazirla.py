"""
Yapay zeka modeli için ortak tablo: her satır = bir tarafın bir tarihte yaptığı kümülatif kayıp iddiası
+ o iddianın hedefi (Oryx'in kanıtladığı kayıp).

İki savaş, dört iddia eden:
  Karabağ 2020   : Azerbaycan -> Ermeni kayıpları, Ermenistan -> Azeri kayıpları   (data/raw/resmi_iddialar.csv)
  Rusya-Ukrayna  : Ukrayna Genelkurmayı -> Rus kayıpları (data/raw/ukrayna_gs_iddialari.json)
                   Rusya Savunma Bak.   -> Ukrayna kayıpları (data/raw/rusya_mod_telegram.csv, Telegram kanalından ~haftalık)

Hedef (gerçeğe en yakın ölçü): iddia tarihinden 60 gün SONRAKİ Oryx sayısı.
  Neden 60 gün? Oryx kayıpları fotoğraf ortaya çıktıkça, gecikmeli ekler. Aynı günkü Oryx gerçek kaybı
  olduğundan az gösterir (Karabağ'da kayıpların ~%40'ı ateşkesten sonra belgelendi).
  Karabağ uçak/helikopter: zaman serisi ikisini ayırmadığı için Oryx nihai sayısı kullanıldı (1'er adet).
Rusya-Ukrayna Oryx serisi kategori bazında Oryx'in kendi başlık toplamlarına kalibre edildi
  (kazıma verisi Oryx'in sonradan sildiği kayıtları da tuttuğu için %3-20 fazla sayıyor).

Ortak kategoriler (iki tarafta aynı 6): zirhli_toplam (tank + diğer zırhlı), topcu, roketatar, hava_savunma, ucak, helikopter.
Çıktı: data/clean/model_tablosu.csv
"""
from pathlib import Path

import json
import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
GECIKME = pd.Timedelta(days=60)
# "tank" ayrı kategori olarak KULLANILMAZ: Rusya tankları ayrı vermiyor ("tanks and other armoured vehicles"),
# iki tarafın aynı 6 kategoriyle karşılaştırılması için tank sadece zirhli_toplam içinde sayılır.
KATEGORILER = ["zirhli_toplam", "topcu", "roketatar", "hava_savunma", "ucak", "helikopter"]
UKRAYNA_ORNEK_GUN = 7    # Ukrayna her gün açıklıyor; Rusya Telegram verisiyle aynı sıklık için haftada bir örnekle


# --------------------------------------------------------------------------- Oryx hedef serileri
def ru_ua_oryx():
    """Rusya-Ukrayna Oryx kümülatif serisi (kalibre edilmiş): {(taraf, kat): pd.Series(tarih -> sayı)}"""
    zs = pd.read_csv(KOK / "data/clean/oryx_ru_ua_zaman_serisi.csv", parse_dates=["tarih"])
    dc = pd.read_csv(KOK / "data/raw/oryx_ru_ua_gunluk_toplam.csv", parse_dates=["date_recorded"])
    dc["equipment_type"] = dc.equipment_type.str.strip()
    acv = dc[dc.equipment_type.str.startswith("Losses of Armoured Combat")].copy()
    acv["type_total"] = acv.equipment_type.str.extract(r"- (\d+),")[0].astype(int)
    acv["equipment_type"] = "ACV"
    dc = pd.concat([dc[~dc.equipment_type.str.startswith("Losses")], acv])
    # Her kategori için Oryx'in kendi başlık toplamı (aynı anlamdaki kategori adı zamanla değişmiş:
    # alternatiflerden EN SON güncelleneni kullanılır, ikisi toplanmaz)
    BASLIK = {
        "tank": [["Tanks"]],
        "zirhli_toplam": [["ACV"]],
        "topcu": [["Self-Propelled Artillery", "Towed Artillery"]],
        "roketatar": [["Rocket and Missile Artillery"], ["Multiple Rocket Launchers"]],
        "hava_savunma": [["Surface-To-Air Missile Systems", "Self-Propelled Anti-Aircraft Guns", "Anti-Aircraft Guns"]],
        "ucak": [["Aircraft"]],
        "helikopter": [["Helicopters"]],
    }
    seriler, kalibrasyon = {}, []
    for ulke, taraf in [("Russia", "Rusya"), ("Ukraine", "Ukrayna")]:
        for kat, alternatifler in BASLIK.items():
            ham_kat = ["tank", "zirhli_arac"] if kat == "zirhli_toplam" else [kat]
            ham = (zs[(zs.kayip_taraf == taraf) & zs.kategori.isin(ham_kat)]
                   .groupby("tarih").kumulatif.sum().sort_index())
            en_iyi = None
            for tipler in alternatifler:
                sub = dc[(dc.country == ulke) & dc.equipment_type.isin(tipler)]
                if sub.empty:
                    continue
                son = sub.sort_values("date_recorded").groupby("equipment_type").last()
                t = son.date_recorded.min()
                if en_iyi is None or t > en_iyi[0]:
                    en_iyi = (t, son.type_total.sum(), tipler)
            t, deger, tipler = en_iyi
            biz = ham[ham.index <= t].iloc[-1]
            oran = deger / biz
            kalibrasyon.append({"taraf": taraf, "kategori": kat, "oryx_baslik": int(deger), "tarih": t.date(),
                                "kazima": int(biz), "kalibrasyon_orani": round(oran, 3), "oryx_tipleri": "+".join(tipler)})
            seriler[(taraf, kat)] = ham * oran
    pd.DataFrame(kalibrasyon).to_csv(KOK / "data/clean/oryx_ru_ua_kalibrasyon.csv", index=False)
    return seriler


def karabag_oryx():
    zs = pd.read_csv(KOK / "data/clean/oryx_zaman_serisi.csv", parse_dates=["tarih"])
    seriler = {}
    for taraf in ["Azerbaycan", "Ermenistan"]:
        for kat in ["tank", "topcu", "roketatar", "hava_savunma"]:
            s = zs[(zs.kayip_taraf == taraf) & (zs.kategori == kat)].set_index("tarih").kumulatif.sort_index()
            if len(s):
                seriler[(taraf, kat)] = s
        s = (zs[(zs.kayip_taraf == taraf) & zs.kategori.isin(["tank", "zirhli_arac"])]
             .groupby("tarih").kumulatif.sum().sort_index())
        seriler[(taraf, "zirhli_toplam")] = s
        # uçak / helikopter: Oryx nihai (An-2 yemler hariç) -> sabit seri
        for kat in ["ucak", "helikopter"]:
            seriler[(taraf, kat)] = pd.Series({pd.Timestamp("2020-09-27"): 1.0})
    return seriler


def deger_al(seri, tarih):
    """tarih anındaki (o güne kadarki son) kümülatif değer"""
    s = seri[seri.index <= tarih]
    return float(s.iloc[-1]) if len(s) else np.nan


# --------------------------------------------------------------------------- iddialar
def karabag_iddialari():
    d = pd.read_csv(KOK / "data/raw/resmi_iddialar.csv", parse_dates=["tarih"])
    d = d[d.durum.isin(["imha", "ele_gecirildi"])]
    d["kat"] = d.proje_kategori
    satirlar = []
    for (tarih, eden, kayip), g in d.groupby(["tarih", "iddia_eden", "kayip_taraf"]):
        top = g.groupby("kat").adet.sum()
        if "zirhli_toplam" not in top and ("tank" in top or "zirhli_arac" in top):
            top["zirhli_toplam"] = top.get("tank", 0) + top.get("zirhli_arac", 0)
        for kat in KATEGORILER:
            if kat in top and top[kat] > 0:
                satirlar.append({"savas": "Karabağ 2020", "iddia_eden": eden, "kayip_taraf": kayip,
                                 "tarih": tarih, "kategori": kat, "iddia": float(top[kat])})
    return pd.DataFrame(satirlar), pd.Timestamp("2020-09-27")


def ukrayna_iddialari():
    d = pd.DataFrame(json.load(open(KOK / "data/raw/ukrayna_gs_iddialari.json")))
    d["tarih"] = pd.to_datetime(d.date)
    d = d.sort_values("tarih")
    d = d[(d.tarih - d.tarih.min()).dt.days % UKRAYNA_ORNEK_GUN == 0]
    d["zirhli_toplam"] = d.tank + d.APC
    esle = {"zirhli_toplam": "zirhli_toplam", "topcu": "field artillery", "roketatar": "MRL",
            "hava_savunma": "anti-aircraft warfare", "ucak": "aircraft", "helikopter": "helicopter"}
    satirlar = []
    for r in d.itertuples(index=False):
        r = r._asdict() if hasattr(r, "_asdict") else dict(zip(d.columns, r))
        for kat, sut in esle.items():
            v = r.get(sut.replace(" ", "_")) if sut.replace(" ", "_") in r else None
            satirlar.append((r["tarih"], kat, sut))
    # itertuples sütun adlarını bozduğu için sözlükle tekrar yap
    satirlar = []
    for _, r in d.iterrows():
        for kat, sut in esle.items():
            if pd.notna(r.get(sut)) and r[sut] > 0:
                satirlar.append({"savas": "Rusya-Ukrayna", "iddia_eden": "Ukrayna", "kayip_taraf": "Rusya",
                                 "tarih": r["tarih"], "kategori": kat, "iddia": float(r[sut])})
    return pd.DataFrame(satirlar), pd.Timestamp("2022-02-24")


def kumulatif_temizle(seri):
    """Kümülatif seri azalamaz. Azalma görülen yerde tek hatalı noktayı at:
    sonraki-sonraki değer de büyükse araya giren düşük değer (çukur) hatalıdır, değilse yüksek değer (sıçrama)."""
    s = seri.dropna().copy()
    while True:
        v = s.values
        bozuk = [i for i in range(len(v) - 1) if v[i] > v[i + 1]]
        if not bozuk:
            return s
        i = bozuk[0]
        at = i + 1 if (i + 2 < len(v) and v[i + 2] >= v[i]) else i
        s = s.drop(s.index[at])


def rusya_iddialari():
    """Rusya Savunma Bakanlığı'nın İngilizce Telegram kanalındaki (t.me/mod_russia_en) günlük raporların
    'toplam' satırı, ~haftalık örneklem (data/raw/rusya_mod_telegram.csv). Kaynak: https://t.me/mod_russia_en/<id>
    TASS'tan elle derlenen data/raw/rusya_mod_iddialari.csv doğrulama için tutuluyor (ortak günlerde birebir aynı)."""
    d = pd.read_csv(KOK / "data/raw/rusya_mod_telegram.csv", parse_dates=["tarih"]).set_index("tarih").sort_index()
    satirlar = []
    for kat in ["ucak", "helikopter", "hava_savunma", "zirhli_toplam", "roketatar", "topcu"]:
        temiz = kumulatif_temizle(d[kat])
        for tarih, v in temiz.items():
            satirlar.append({"savas": "Rusya-Ukrayna", "iddia_eden": "Rusya", "kayip_taraf": "Ukrayna",
                             "tarih": tarih, "kategori": kat, "iddia": float(v),
                             "kaynak_url": f"https://t.me/mod_russia_en/{int(d.loc[tarih, 'id'])}"})
    return pd.DataFrame(satirlar), pd.Timestamp("2022-02-24")


# --------------------------------------------------------------------------- birleştir
def main():
    oryx = {**ru_ua_oryx(), **karabag_oryx()}
    son_oryx_tarihi = {"Rusya-Ukrayna": pd.Timestamp("2025-08-21"), "Karabağ 2020": pd.Timestamp("2021-01-31")}
    parcalar = []
    for fonk in (karabag_iddialari, ukrayna_iddialari, rusya_iddialari):
        df, baslangic = fonk()
        df["savas_gunu"] = (df.tarih - baslangic).dt.days + 1
        parcalar.append(df)
    t = pd.concat(parcalar, ignore_index=True)

    # Hedef: 60 gün sonraki Oryx (Oryx verisinin bittiği tarihi aşan iddialar atılır)
    t["hedef_tarih"] = t.tarih + GECIKME
    t = t[t.hedef_tarih <= t.savas.map(son_oryx_tarihi)].copy()
    t["oryx_hedef"] = [deger_al(oryx[(k, c)], h) if (k, c) in oryx else np.nan
                       for k, c, h in zip(t.kayip_taraf, t.kategori, t.hedef_tarih)]
    t["oryx_ayni_gun"] = [deger_al(oryx[(k, c)], d) if (k, c) in oryx else np.nan
                          for k, c, d in zip(t.kayip_taraf, t.kategori, t.tarih)]
    t = t[t.oryx_hedef >= 1].copy()

    # Özellikler
    t = t.sort_values(["iddia_eden", "kategori", "tarih"])
    onceki = t.groupby(["iddia_eden", "kategori"])[["iddia", "tarih"]].shift(1)
    gun_fark = (t.tarih - onceki.tarih).dt.days
    t["artis_hizi"] = np.where(gun_fark > 0, np.log(t.iddia / onceki.iddia) / gun_fark * 30, 0.0)  # ayda log-artış
    t["artis_hizi"] = t.artis_hizi.fillna(0.0)
    t["log_iddia"] = np.log10(t.iddia)
    t["log_gun"] = np.log10(t.savas_gunu)
    t["saldiran"] = t.iddia_eden.isin(["Azerbaycan", "Rusya"]).astype(int)
    t["abartma"] = t.iddia / t.oryx_hedef
    t["log_abartma"] = np.log10(t.abartma)

    t.to_csv(KOK / "data/clean/model_tablosu.csv", index=False)
    print(t.groupby(["savas", "iddia_eden"]).size().rename("satir").to_string())
    print()
    print(t.groupby(["iddia_eden", "kategori"]).abartma.median().unstack().round(2).to_string())
    return t


if __name__ == "__main__":
    main()
