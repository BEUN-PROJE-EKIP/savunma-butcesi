"""
Üç savaş, tek tablo: silah türü -> hedef türü -> verilen kaybın değeri.

Kaynaklar
  - Karabağ 2020 : Oryx, vuran silahı belli 669 kayıp (TB2, dolanan mühimmat, Spike).
  - Rusya-Ukrayna: LostArmour, 5.196 videolu Lancet saldırısı (imha/hasar/ıska/bilinmiyor).
  - İran-ABD 2026: CRS IN12692 (5 Ekim 2026) — 81 ABD uçağı; nedeni İran silahına bağlanabilenler
                   (data/raw/silah_hedef/iran_abd_kayiplar.csv). Dost ateşi, kaza ve kendi kuvvetlerince
                   imha edilenler HARİÇ. 45 MQ-9'un nedeni belirtilmemiş: ayrı gösterilir.
Değer
  - Karabağ ve Lancet hedefleri: birim_maliyetler.csv merkez fiyatları (aynı tablo; tutarlılık için).
  - İran-ABD: CBO / basın yerine koyma maliyetleri (ABD uçakları) — bu nedenle ölçek farklıdır.
  - imha / ele geçirme = değerin tamamı; hasar = k (merkez 0,3); hafif hasar 0,05 (İran verisinde satır bazında).
  - Lancet'te sonucu "bilinmiyor" olan saldırılara değer verilmez (alt sınır).
Bu bir "atış başına verim" analizi DEĞİLDİR (Karabağ ve İran'da atılan mühimmat sayısı yok);
her silahın hangi hedeflere ne kadar kayıp verdirdiğini gösterir.

Çıktı: data/clean/silah_hedef_deger.csv, results/uc_savas_ozet.csv, results/grafik_11_uc_savas.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
METIN, METIN2, IZGARA, ZEMIN = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
RENK_SAVAS = {"Karabağ 2020": "#2a78d6", "Rusya-Ukrayna": "#eb6834", "İran-ABD 2026": "#1f9e6e"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "axes.edgecolor": IZGARA,
                     "xtick.color": METIN2, "ytick.color": METIN2, "axes.facecolor": ZEMIN,
                     "figure.facecolor": ZEMIN, "savefig.facecolor": ZEMIN})

HEDEF_GRUP = {  # ortak hedef / alt hedef -> grafikteki grup
    "tank": "Tank", "zirhli_arac": "Zırhlı araç", "hafif_zirhli": "Zırhlı araç", "topcu": "Topçu",
    "cekili_top": "Topçu", "kundagi_motorlu_top": "Topçu", "roketatar": "Roketatar",
    "hava_savunma": "Hava savunma", "hs_fuze": "Hava savunma", "hs_top": "Hava savunma",
    "radar_eh": "Radar / EH", "radar": "Radar / EH", "lojistik_arac": "Lojistik araç", "arac": "Lojistik araç",
    "ozel_arac": "Lojistik araç", "deniz_araci": "Diğer", "yem": "Diğer", "maket": "Diğer",
    "ucak_yerde": "Uçak (yerde)", "ucak_havada": "Uçak (havada)", "iha": "İHA / helikopter",
    "helikopter": "İHA / helikopter",
}
FIYAT_ESLE = {  # Karabağ ortak hedef -> birim_maliyetler kalemi
    "tank": "tank", "zirhli_arac": "hafif_zirhli", "topcu": "cekili_top", "roketatar": "roketatar",
    "hava_savunma": "hs_fuze", "radar_eh": "radar", "lojistik_arac": "arac", "yem": "maket",
}
GRUPLAR = ["Tank", "Zırhlı araç", "Topçu", "Roketatar", "Hava savunma", "Radar / EH", "Lojistik araç",
           "Uçak (yerde)", "Uçak (havada)", "İHA / helikopter", "Diğer"]


def satirlar():
    m = pd.read_csv(KOK / "data/raw/silah_hedef/birim_maliyetler.csv").set_index("kalem")
    fiyat = m.merkez_usd
    k = float(m.loc["hasar_kayip_orani", "merkez_usd"])
    pay = {"imha": 1.0, "ele_gecirildi": 1.0, "terk": 1.0, "hasar": k, "iska": 0.0, "bilinmiyor": 0.0}
    sh = pd.read_csv(KOK / "data/clean/silah_hedef.csv")
    out = []
    # Karabağ
    kb = sh[sh.kaynak == "Oryx"]
    ad_kb = {"SİHA (TB2)": "SİHA (TB2)", "dolanan_muhimmat": "Dolanan mühimmat (Harop vb.)",
             "tanksavar_fuze": "Tanksavar füze (Spike)"}
    for _, r in kb.iterrows():
        kal = FIYAT_ESLE.get(r.hedef)
        deger = fiyat[kal] if kal else 0.0
        out.append({"savas": "Karabağ 2020", "silah": ad_kb[r.silah], "hedef_grup": HEDEF_GRUP.get(r.hedef, "Diğer"),
                    "adet": r.adet, "kayip_usd": r.adet * pay.get(r.sonuc, 0) * deger, "fiyatsiz": kal is None})
    # Lancet
    la = sh[sh.kaynak == "LostArmour"]
    for _, r in la.iterrows():
        deger = fiyat.get(r.hedef_alt, 0.0)
        out.append({"savas": "Rusya-Ukrayna", "silah": "Dolanan mühimmat (Lancet)",
                    "hedef_grup": HEDEF_GRUP.get(r.hedef_alt, HEDEF_GRUP.get(r.hedef, "Diğer")),
                    "adet": 1, "kayip_usd": pay.get(r.sonuc, 0) * deger, "fiyatsiz": r.hedef_alt not in fiyat.index,
                    "sonuc": r.sonuc})
    # İran-ABD
    ia = pd.read_csv(KOK / "data/raw/silah_hedef/iran_abd_kayiplar.csv")
    ad_ia = {"balistik_fuze": "Balistik füze (üs saldırısı)", "hava_savunma": "Hava savunma / yer ateşi",
             "belirsiz": "Nedeni belirtilmemiş (MQ-9)"}
    for _, r in ia[ia.silah != "HARIC"].iterrows():
        out.append({"savas": "İran-ABD 2026", "silah": ad_ia[r.silah], "hedef_grup": HEDEF_GRUP[r.hedef],
                    "adet": r.adet, "kayip_usd": r.adet * r.hasar_payi * r.birim_deger_usd, "fiyatsiz": False})
    return pd.DataFrame(out)


def main():
    t = satirlar()
    t.to_csv(KOK / "data/clean/silah_hedef_deger.csv", index=False)
    oz = t.groupby(["savas", "silah"]).agg(kayit=("adet", "sum"), kayip_musd=("kayip_usd", lambda x: x.sum() / 1e6))
    pv = t.pivot_table(index=["savas", "silah"], columns="hedef_grup", values="kayip_usd", aggfunc="sum", fill_value=0)
    pv = pv.reindex(columns=[g for g in GRUPLAR if g in pv.columns])
    paylar = (100 * pv.div(pv.sum(1), axis=0)).round(0)
    oz = oz.join(paylar.add_prefix("pay_%_"))
    oz["kayip_musd"] = oz.kayip_musd.round(0)
    oz.to_csv(KOK / "results/uc_savas_ozet.csv")
    print(oz.to_string())
    grafik(oz, paylar)


def grafik(oz, paylar):
    sira = [("Karabağ 2020", "SİHA (TB2)"), ("Karabağ 2020", "Dolanan mühimmat (Harop vb.)"),
            ("Karabağ 2020", "Tanksavar füze (Spike)"), ("Rusya-Ukrayna", "Dolanan mühimmat (Lancet)"),
            ("İran-ABD 2026", "Balistik füze (üs saldırısı)"), ("İran-ABD 2026", "Hava savunma / yer ateşi"),
            ("İran-ABD 2026", "Nedeni belirtilmemiş (MQ-9)")]
    sira = [s for s in sira if s in oz.index]
    etiket = [f"{s[1]}\n{s[0]}" for s in sira]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 8), gridspec_kw={"width_ratios": [1.0, 1.3]})
    fig.subplots_adjust(top=0.80, bottom=0.16, left=0.17, right=0.98, wspace=0.06)
    fig.text(0.02, 0.94, "Üç savaş: hangi silah türü neyi vurdu, ne kadarlık kayıp verdirdi?",
             fontsize=18, color=METIN, fontweight="bold")
    fig.text(0.02, 0.885, "Sol: belgelenmiş kayıpların toplam değeri (milyon $, log ölçek; çubuk üstü = kayıt sayısı). "
             "Sağ: o kaybın hedef türlerine dağılımı (%).", fontsize=12, color=METIN2)
    y = np.arange(len(sira))[::-1]
    v = [oz.loc[s, "kayip_musd"] for s in sira]
    renk = [RENK_SAVAS[s[0]] for s in sira]
    a1.barh(y, v, height=0.6, color=renk)
    for yi, vi, s in zip(y, v, sira):
        a1.text(vi * 1.1, yi, f"{vi:,.0f} mn $  ({int(oz.loc[s, 'kayit']):,} kayıt)".replace(",", "."),
                va="center", fontsize=10, color=METIN)
    a1.set_xscale("log")
    a1.set_xlim(1, max(v) * 200)
    a1.set_yticks(y, etiket, fontsize=10.5)
    a1.set_xlabel("Belgelenmiş kaybın değeri (milyon $)")
    a1.grid(axis="x", color=IZGARA, linewidth=0.8)
    a1.set_axisbelow(True)
    for s in ["top", "right"]:
        a1.spines[s].set_visible(False)
    # sağ: ısı haritası
    P = paylar.reindex(sira).fillna(0)
    sutun = [g for g in GRUPLAR if g in P.columns and P[g].max() > 0]
    M = P[sutun].values
    a2.imshow(M, aspect="auto", cmap="Blues", vmin=0, vmax=100)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if M[i, j] >= 1:
                a2.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=10,
                        color="white" if M[i, j] > 55 else METIN)
    a2.set_xticks(range(len(sutun)), sutun, rotation=35, ha="right", fontsize=10.5)
    a2.set_yticks([])
    for sp in a2.spines.values():
        sp.set_visible(False)
    a2.set_xticks(np.arange(-0.5, len(sutun)), minor=True)
    a2.set_yticks(np.arange(-0.5, len(sira)), minor=True)
    a2.grid(which="minor", color=ZEMIN, linewidth=2)
    a2.tick_params(which="minor", length=0)
    fig.text(0.02, 0.03, "Kaynak: Oryx (Karabağ), LostArmour (Lancet), CRS IN12692 ve CBO (İran-ABD). Fiyatlar yaklaşık; "
             "İran-ABD'de yerine koyma maliyeti kullanıldı. Atış başına verim değildir: atılan mühimmat sayısı yalnızca Lancet'te biliniyor.",
             fontsize=9.5, color=METIN2)
    fig.savefig(KOK / "results/grafik_11_uc_savas.png", dpi=150)


if __name__ == "__main__":
    main()
