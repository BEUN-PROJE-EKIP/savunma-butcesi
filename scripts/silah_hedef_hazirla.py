"""
Silah türü -> hedef türü -> sonuç tablosu (taraftan bağımsız).

Her satır bir saldırı ya da bir kayıp kaydıdır; kim attığı değil NE ile NEYİN vurulduğu ve sonucu tutulur.

Kaynaklar
  1) LostArmour Lancet tablosu  (data/raw/silah_hedef/lancet_saldirilari.csv)
     lostarmour.info/lancet, 9 Kasım 2026'da Claude uygulamasının tarayıcısıyla tablo olarak indirildi.
     Her satır videolu bir Lancet saldırısı; etiketlerde hedef türü, sonuç, model, hareketli hedef vb. var.
     Sonuçlar: imha / hasar / iska / bilinmiyor  -> IMHA OLASILIĞI hesaplanabilir.
  2) Oryx Karabağ 2020 (data/clean/oryx_karabag_ozet.csv), "vuran_silah" belli olan kayıtlar
     (TB2, dolanan mühimmat, Spike ATGM). Oryx sadece KAYIPLARI listeler, ıska yoktur:
     bu kaynak imha olasılığı için değil, silahın HEDEF KARIŞIMI için kullanılır.

Çıktı: data/clean/silah_hedef.csv
  savas, kaynak, yil, silah, silah_alt, hedef, hedef_alt, sonuc, hareketli, adet, kanit_url
"""
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parent.parent

# LostArmour etiketi -> (ortak hedef, alt hedef)
LA_HEDEF = {
    "орудие": ("topcu", "cekili_top"), "САУ": ("topcu", "kundagi_motorlu_top"),
    "танк": ("tank", "tank"), "ЛБ": ("zirhli_arac", "hafif_zirhli"),
    "автотранспорт": ("lojistik_arac", "arac"), "спецтехника": ("lojistik_arac", "ozel_arac"),
    "РЛС": ("radar_eh", "radar"), "ЗРК": ("hava_savunma", "hs_fuze"), "ЗСУ": ("hava_savunma", "hs_top"),
    "РСЗО": ("roketatar", "roketatar"), "плавсредство": ("deniz_araci", "deniz_araci"),
    "здание": ("mevzi_bina", "bina"), "позиция": ("mevzi_bina", "mevzi"), "пехота": ("piyade", "piyade"),
    "БПЛА": ("iha", "iha"), "самолет": ("hava_araci", "ucak"), "вертолет": ("hava_araci", "helikopter"),
    "макет": ("yem", "maket"), "прочее": ("diger", "diger"), "неидентифицирован": ("belirsiz", "belirsiz"),
}
LA_SONUC = {"уничтожен": "imha", "поврежден": "hasar", "промах": "iska", "неизвестен": "bilinmiyor"}

# Oryx Karabağ proje kategorisi -> ortak hedef
KB_HEDEF = {"tank": "tank", "zirhli_arac": "zirhli_arac", "topcu": "topcu", "roketatar": "roketatar",
            "hava_savunma": "hava_savunma", "lojistik": "lojistik_arac", "elektronik_harp": "radar_eh",
            "hava_araci": "hava_araci", "iha": "iha", "yem": "yem", "tanksavar": "diger",
            "balistik_fuze": "diger", "diger": "diger"}
KB_SONUC = {"imha": "imha", "hasarli": "hasar", "ele_gecirildi": "ele_gecirildi", "terk": "terk", "diger": "diger"}
KB_SILAH = {"TB2": ("SİHA (TB2)", "TB2"), "dolanan_muhimmat": ("dolanan_muhimmat", "Harop/SkyStriker vb."),
            "Spike_ATGM": ("tanksavar_fuze", "Spike")}


def lancet():
    d = pd.read_csv(KOK / "data/raw/silah_hedef/lancet_saldirilari.csv", encoding="utf-8-sig")
    satir = []
    for _, r in d.iterrows():
        et = [e.strip() for e in str(r.etiketler).replace(".", ",").split(",")]
        h = next((LA_HEDEF[e] for e in et if e in LA_HEDEF), ("belirsiz", "belirsiz"))
        s = next((LA_SONUC[e] for e in et if e in LA_SONUC), "bilinmiyor")
        m = next((e for e in et if e.startswith("мод_")), "мод_?").replace("мод_", "")
        m = {"н": "yeni"}.get(m, m.replace("х", "x"))
        satir.append({"savas": "Rusya-Ukrayna", "kaynak": "LostArmour", "yil": int(str(r.tarih)[:4]),
                      "tarih": r.tarih, "silah": "dolanan_muhimmat", "silah_alt": f"Lancet-{m}",
                      "hedef": h[0], "hedef_alt": h[1], "sonuc": s,
                      "hareketli": int("_движущаяся" in et), "adet": 1, "kanit_url": r.url})
    return pd.DataFrame(satir)


def karabag():
    d = pd.read_csv(KOK / "data/clean/oryx_karabag_ozet.csv")
    d = d[d.vuran_silah.isin(KB_SILAH)]
    return pd.DataFrame({
        "savas": "Karabağ 2020", "kaynak": "Oryx", "yil": 2020, "tarih": None,
        "silah": d.vuran_silah.map(lambda s: KB_SILAH[s][0]), "silah_alt": d.vuran_silah.map(lambda s: KB_SILAH[s][1]),
        "hedef": d.proje_kategori.map(KB_HEDEF).fillna("diger"), "hedef_alt": d.model,
        "sonuc": d.durum.map(KB_SONUC).fillna("diger"), "hareketli": None, "adet": d.adet, "kanit_url": None,
    })


def main():
    t = pd.concat([lancet(), karabag()], ignore_index=True)
    (KOK / "data/clean").mkdir(parents=True, exist_ok=True)
    t.to_csv(KOK / "data/clean/silah_hedef.csv", index=False)
    print("Toplam kayıt (adet):", int(t.adet.sum()))
    print(t.groupby(["savas", "silah"]).adet.sum().to_string())
    print("\nHedef x sonuç (adet):")
    print(t.pivot_table(index="hedef", columns="sonuc", values="adet", aggfunc="sum", fill_value=0).to_string())


if __name__ == "__main__":
    main()
