"""
Sunum grafikleri: resmi iddia vs medya ("kalabalık") vs gerçeğe en yakın referans (Oryx / UCDP).

Girdiler: data/raw/resmi_iddialar.csv, data/clean/medya_iddialari.csv, data/clean/oryx_zaman_serisi.csv,
          data/clean/oryx_karabag_ozet.csv, data/clean/ucdp_karabag.csv, results/medya_ozet.csv
Çıktılar: results/grafik_1_ermeni_tank.png ... grafik_5_ozet.png  (16:9, sunuma hazır)

Kullanım:  python scripts/grafikler.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, LogLocator

KOK = Path(__file__).resolve().parent.parent
SONUC = KOK / "results"

# Renkler (doğrulanmış varsayılan paletin ilk üç kategorik rengi + nötr gri)
RESMI = "#2a78d6"      # mavi  : resmi iddia
TARAFLI = "#eb6834"    # turuncu: iddia eden tarafın medyası
ORYX = "#1baf7a"       # su yeşili: Oryx / UCDP (gerçeğe en yakın referans)
DIGER = "#9a9893"      # gri  : diğer medya
METIN, METIN2, IZGARA, ZEMIN = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
ATESKES = pd.Timestamp("2020-11-10")
BAS, BIT = pd.Timestamp("2020-09-25"), pd.Timestamp("2020-12-05")

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 13, "axes.edgecolor": IZGARA, "axes.labelcolor": METIN2,
    "xtick.color": METIN2, "ytick.color": METIN2, "axes.facecolor": ZEMIN, "figure.facecolor": ZEMIN,
    "savefig.facecolor": ZEMIN,
})

iddia = pd.read_csv(KOK / "data/raw/resmi_iddialar.csv", parse_dates=["tarih"])
medya = pd.read_csv(KOK / "data/clean/medya_iddialari.csv", parse_dates=["tarih"])
oryx_zs = pd.read_csv(KOK / "data/clean/oryx_zaman_serisi.csv", parse_dates=["tarih"])
oryx = pd.read_csv(KOK / "data/clean/oryx_karabag_ozet.csv")
ucdp = pd.read_csv(KOK / "data/clean/ucdp_karabag.csv")
ozet = pd.read_csv(KOK / "results/medya_ozet.csv")

ETIKET = {"Azerbaycan": "Azerbaycan", "Ermenistan": "Ermenistan"}
KARSI = {"Azerbaycan": "Ermenistan", "Ermenistan": "Azerbaycan"}


def sayi_fmt(x, _):
    return f"{x:,.0f}".replace(",", ".") if x >= 1 else f"{x:g}"


def eksen_hazirla(ax, baslik, alt_baslik, log=True):
    ax.set_title(baslik, loc="left", fontsize=19, color=METIN, pad=34, fontweight="bold")
    ax.text(0, 1.035, alt_baslik, transform=ax.transAxes, fontsize=12.5, color=METIN2, va="bottom")
    if log:
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1, 2, 5)))
        ax.yaxis.set_minor_locator(plt.NullLocator())
    ax.yaxis.set_major_formatter(FuncFormatter(sayi_fmt))
    ax.grid(axis="y", color=IZGARA, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)


def tarih_ekseni(ax):
    ax.set_xlim(BAS, BIT)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: tr_tarih(mdates.num2date(x))))
    ax.axvline(ATESKES, color=METIN2, linewidth=1, linestyle=(0, (3, 3)))
    ax.text(ATESKES, 1.0, " Ateşkes", transform=ax.get_xaxis_transform(), color=METIN2, fontsize=11,
            va="top", ha="left")


AYLAR = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def tr_tarih(t):
    return f"{t.day} {AYLAR[t.month]}"


def resmi_seri(kayip_taraf, kategoriler):
    d = iddia[(iddia.kayip_taraf == kayip_taraf) & iddia.proje_kategori.isin(kategoriler)
              & iddia.durum.isin(["imha", "ele_gecirildi"])]
    return d.groupby("tarih").adet.sum().sort_index()


def oryx_seri(kayip_taraf, kategoriler):
    d = oryx_zs[(oryx_zs.kayip_taraf == kayip_taraf) & oryx_zs.kategori.isin(kategoriler)]
    return d.groupby("tarih").kumulatif.sum().sort_index()


def oryx_nihai(kayip_taraf, kategoriler):
    return oryx[(oryx.kayip_taraf == kayip_taraf) & oryx.proje_kategori.isin(kategoriler)].adet.sum()


def uc_etiket(ax, x, y, metin, renk, dy=0):
    ax.annotate(metin, (x, y), xytext=(8, dy), textcoords="offset points", color=METIN, fontsize=12,
                va="center", ha="left", fontweight="bold")
    ax.plot([x], [y], "o", color=renk, markersize=8, markeredgecolor=ZEMIN, markeredgewidth=2, zorder=5)


def zaman_grafigi(dosya, baslik, alt, kayip_taraf, resmi_kat, medya_kat, oryx_kat, iddia_eden_ad, not_metni=None):
    fig, ax = plt.subplots(figsize=(13.33, 7.5))
    fig.subplots_adjust(left=0.07, right=0.84, top=0.84, bottom=0.22)
    eksen_hazirla(ax, baslik, alt)

    # Medya noktaları: iddia eden tarafın medyası turuncu, diğerleri gri
    m = medya[(medya.kayip_taraf == kayip_taraf) & medya.proje_kategori.isin(medya_kat)]
    tarafli = m.iddia_eden == KARSI[kayip_taraf]
    jitter = pd.to_timedelta(np.random.default_rng(1).uniform(-8, 8, len(m)), unit="h")
    ax.scatter(m.tarih[~tarafli] + jitter[~tarafli.values], m.adet[~tarafli], s=34, color=DIGER, alpha=0.55,
               edgecolors=ZEMIN, linewidths=0.8, zorder=2, label="Haberdeki sayı: diğer medya")
    ax.scatter(m.tarih[tarafli] + jitter[tarafli.values], m.adet[tarafli], s=48, color=TARAFLI, alpha=0.9,
               edgecolors=ZEMIN, linewidths=0.8, zorder=3, label=f"Haberdeki sayı: {iddia_eden_ad} medyası")

    # Oryx kümülatif (savaş sırasında o gün kanıtlanmış) + nihai
    o = oryx_seri(kayip_taraf, oryx_kat)
    ax.step(o.index, o.values, where="post", color=ORYX, linewidth=2.5, zorder=4,
            label="Oryx: o güne kadar kanıtlanan")
    son = oryx_nihai(kayip_taraf, oryx_kat)
    ax.axhline(son, color=ORYX, linewidth=1.5, linestyle=(0, (6, 3)), zorder=1)
    uc_etiket(ax, BIT, son, f"Oryx nihai: {son}", ORYX)

    # Resmi iddia
    r = resmi_seri(kayip_taraf, resmi_kat)
    if len(r):
        ax.step(r.index, r.values, where="post", color=RESMI, linewidth=2.5, zorder=4,
                label=f"{iddia_eden_ad} resmi iddiası")
        ax.plot(r.index, r.values, "o", color=RESMI, markersize=8, markeredgecolor=ZEMIN, markeredgewidth=2, zorder=5)
        uc_etiket(ax, BIT, r.iloc[-1], f"Resmi iddia: {r.iloc[-1]}", RESMI, dy=0)
        ax.plot([r.index[-1], BIT], [r.iloc[-1]] * 2, color=RESMI, linewidth=1.5, linestyle=(0, (1, 2)))

    tarih_ekseni(ax)
    ax.set_ylim(1, max(m.adet.max() if len(m) else 1, r.max() if len(r) else 1, son) * 2)
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, -0.07), ncol=2, frameon=False, fontsize=11.5, labelcolor=METIN2,
              handlelength=1.6, columnspacing=1.6)
    fig.text(0.07, 0.02, "Kaynak: GDELT GKG 2.0 (saatlik örneklem), resmi açıklamalar, Oryx. Dikey eksen logaritmik."
             + (f"\n{not_metni}" if not_metni else ""), fontsize=10.5, color=METIN2, va="bottom")
    fig.savefig(SONUC / dosya, dpi=150)
    plt.close(fig)
    print("->", dosya)


def olu_grafigi():
    fig, eksenler = plt.subplots(1, 2, figsize=(13.33, 7.5), sharey=True)
    fig.subplots_adjust(left=0.07, right=0.97, top=0.80, bottom=0.14, wspace=0.08)
    fig.text(0.07, 0.93, "Asker ölüleri: medyadaki tipik sayı, gerçek kaybın yalnızca %8'i",
             fontsize=19, color=METIN, fontweight="bold")
    fig.text(0.07, 0.885, "Her nokta bir haberde geçen ölü sayısı. Yeşil çizgi: UCDP'nin savaş sonrası en iyi tahmini.",
             fontsize=12.5, color=METIN2)
    ucdp_olu = {"Ermenistan": ucdp.deaths_b.sum(), "Azerbaycan": ucdp.deaths_a.sum()}
    for ax, taraf in zip(eksenler, ["Ermenistan", "Azerbaycan"]):
        eksen_hazirla(ax, "", "")
        ax.set_title(f"{taraf} tarafının asker kaybı", loc="left", fontsize=14, color=METIN, pad=10)
        m = medya[(medya.kayip_taraf == taraf) & (medya.proje_kategori == "asker_olu")]
        tarafli = m.iddia_eden.notna()
        jitter = pd.to_timedelta(np.random.default_rng(2).uniform(-8, 8, len(m)), unit="h")
        ax.scatter(m.tarih[~tarafli] + jitter[~tarafli.values], m.adet[~tarafli], s=30, color=DIGER, alpha=0.55,
                   edgecolors=ZEMIN, linewidths=0.8, label="Uluslararası medya")
        ax.scatter(m.tarih[tarafli] + jitter[tarafli.values], m.adet[tarafli], s=44, color=TARAFLI, alpha=0.9,
                   edgecolors=ZEMIN, linewidths=0.8, label="Ermeni / Azeri-Türk medyası")
        ax.axhline(ucdp_olu[taraf], color=ORYX, linewidth=2.5)
        ax.text(BAS + pd.Timedelta(days=1), ucdp_olu[taraf] * 1.18, f"UCDP: {ucdp_olu[taraf]:,}".replace(",", "."),
                color=METIN, fontsize=12, fontweight="bold")
        med = ozet[(ozet.kayip_taraf == taraf) & (ozet.proje_kategori == "asker_olu") & (ozet.medya_grubu == "HEPSİ")]
        if len(med):
            v = med.kalabalik_medyan.iloc[0]
            ax.axhline(v, color=TARAFLI, linewidth=1.5, linestyle=(0, (6, 3)))
            ax.text(BAS + pd.Timedelta(days=1), v * 1.25, f"Medya medyanı: {v:,.0f}".replace(",", "."),
                    color=METIN, fontsize=12, fontweight="bold")
        tarih_ekseni(ax)
        ax.set_ylim(1, 20000)
    eksenler[0].legend(loc="lower right", frameon=False, fontsize=11, labelcolor=METIN2)
    fig.text(0.07, 0.035, "Kaynak: GDELT GKG 2.0 (saatlik örneklem), UCDP GED 26.1. Dikey eksen logaritmik.",
             fontsize=10.5, color=METIN2)
    fig.savefig(SONUC / "grafik_4_asker_olu.png", dpi=150)
    plt.close(fig)
    print("-> grafik_4_asker_olu.png")


def ozet_grafigi():
    """Her kategori için resmi iddia ve medya medyanı, referansın kaç katı?"""
    satirlar = [  # (etiket, kayip_taraf, ozet kategorisi)
        ("Ermeni tankı", "Ermenistan", "tank"),
        ("Ermeni topçusu", "Ermenistan", "topcu"),
        ("Ermeni hava savunması", "Ermenistan", "hava_savunma"),
        ("Azeri tank + zırhlı", "Azerbaycan", "zirhli_toplam"),
        ("Azeri İHA", "Azerbaycan", "iha"),
        ("Azeri helikopter", "Azerbaycan", "helikopter"),
        ("Ermeni asker ölüsü", "Ermenistan", "asker_olu"),
        ("Azeri asker ölüsü", "Azerbaycan", "asker_olu"),
    ]
    h = ozet[ozet.medya_grubu == "HEPSİ"].set_index(["kayip_taraf", "proje_kategori"])
    fig, ax = plt.subplots(figsize=(13.33, 7.5))
    fig.subplots_adjust(left=0.22, right=0.95, top=0.80, bottom=0.16)
    eksen_hazirla(ax, "Kim gerçeğe ne kadar yakın?",
                  "1 = gerçeğe en yakın referans (ekipman: Oryx nihai, ölüler: UCDP). Sağ = abartma, sol = eksik sayma.",
                  log=False)
    ax.set_xscale("log")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=IZGARA, linewidth=0.8)
    ax.axvline(1, color=ORYX, linewidth=2.5, zorder=1)
    for i, (et, t, k) in enumerate(satirlar):
        y = len(satirlar) - 1 - i
        r = h.loc[(t, k)] if (t, k) in h.index else None
        if r is None:
            continue
        x_m = r.kalabalik_bolu_ref
        x_r = r.resmi_bolu_ref
        noktalar = [v for v in (x_m, x_r) if pd.notna(v)]
        ax.plot([min(noktalar + [1]), max(noktalar + [1])], [y, y], color=IZGARA, linewidth=2, zorder=1)
        if pd.notna(x_r):
            ax.plot(x_r, y, "o", color=RESMI, markersize=13, markeredgecolor=ZEMIN, markeredgewidth=2, zorder=3)
            yakin = 0.8 < x_r < 1.3   # yeşil çizgiye çok yakınsa etiketi sağa kaydır
            ax.annotate(f"{x_r:.1f}×", (x_r, y), xytext=(14, 0) if yakin else (0, 13), textcoords="offset points",
                        ha="left" if yakin else "center", va="center" if yakin else "baseline",
                        fontsize=11, color=METIN)
        ax.plot(x_m, y, "D", color=TARAFLI, markersize=11, markeredgecolor=ZEMIN, markeredgewidth=2, zorder=3)
        ax.annotate(f"{x_m:.2f}×" if x_m < 1 else f"{x_m:.1f}×", (x_m, y), xytext=(0, -19),
                    textcoords="offset points", ha="center", fontsize=11, color=METIN)
    ax.set_yticks(range(len(satirlar)))
    ax.set_yticklabels([s[0] for s in reversed(satirlar)], fontsize=13, color=METIN)
    ax.set_xlim(0.01, 200)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}×"))
    ax.set_ylim(-0.7, len(satirlar) - 0.3)
    ax.plot([], [], "o", color=RESMI, markersize=11, label="Karşı tarafın resmi iddiası")
    ax.plot([], [], "D", color=TARAFLI, markersize=10, label="Medya medyanı (kalabalık tahmini)")
    ax.legend(loc="lower right", frameon=False, fontsize=12, labelcolor=METIN2)
    fig.text(0.22, 0.04, "Kaynak: resmi açıklamalar, GDELT GKG 2.0, Oryx, UCDP. Yatay eksen logaritmik. "
             "Ölüler için resmi savaş-içi iddia verisi yok.", fontsize=10.5, color=METIN2)
    fig.savefig(SONUC / "grafik_5_ozet.png", dpi=150)
    plt.close(fig)
    print("-> grafik_5_ozet.png")


if __name__ == "__main__":
    zaman_grafigi("grafik_1_ermeni_tank.png",
                  "Ermeni tank kaybı: Azerbaycan iddiası Oryx'e yakın, medya dağınık",
                  "Azerbaycan'ın imha + ele geçirildi iddiası, haberlerde geçen sayılar ve Oryx'in kanıtladığı kayıp",
                  "Ermenistan", ["tank"], ["tank"], ["tank"], "Azerbaycan / Türk")
    zaman_grafigi("grafik_2_azeri_zirhli.png",
                  "Azeri tank + zırhlı kaybı: Ermeni iddiası Oryx'in 4 katı",
                  "Ermenistan'ın 'tank ve zırhlı araç' iddiası, haberlerde geçen sayılar ve Oryx'in kanıtladığı kayıp",
                  "Azerbaycan", ["zirhli_toplam"], ["tank", "zirhli_toplam", "zirhli_arac"], ["tank", "zirhli_arac"],
                  "Ermeni")
    zaman_grafigi("grafik_3_azeri_iha.png",
                  "Azeri İHA kaybı: 264 iddia, 4 kanıt",
                  "Ermenistan'ın İHA iddiası, haberlerde geçen sayılar ve Oryx'in kanıtladığı kayıp",
                  "Azerbaycan", ["iha"], ["iha"], ["iha"], "Ermeni",
                  not_metni="Oryx savaş sırasında dolanan mühimmatları da İHA sayıyordu, sonra çıkardı.")
    olu_grafigi()
    ozet_grafigi()
