"""
Model grafikleri (16:9, sunuma hazır):
  results/grafik_6_abartma_zaman.png : dört tarafın abartma oranı (iddia / Oryx) savaş boyunca
  results/grafik_7_model_sonuclari.png : üç deneyde modellerin medyan kat hatası
Girdi: data/clean/model_tablosu.csv, results/model_sonuclari.csv
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

KOK = Path(__file__).resolve().parent.parent
SONUC = KOK / "results"
METIN, METIN2, IZGARA, ZEMIN = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
# doğrulanmış varsayılan paletin ilk dört kategorik rengi (sıra sabit)
RENK = {"Ukrayna": "#2a78d6", "Rusya": "#eb6834", "Azerbaycan": "#1baf7a", "Ermenistan": "#eda100"}
ETIKET = {"Ukrayna": "Ukrayna (Rus kayıpları)", "Rusya": "Rusya (Ukrayna kayıpları)",
          "Azerbaycan": "Azerbaycan (Ermeni kayıpları)", "Ermenistan": "Ermenistan (Azeri kayıpları)"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "axes.edgecolor": IZGARA,
                     "axes.labelcolor": METIN2, "xtick.color": METIN2, "ytick.color": METIN2,
                     "axes.facecolor": ZEMIN, "figure.facecolor": ZEMIN, "savefig.facecolor": ZEMIN})
kat_fmt = FuncFormatter(lambda x, _: f"{x:g}×")


def sade(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.set_axisbelow(True)


def abartma_zaman():
    t = pd.read_csv(KOK / "data/clean/model_tablosu.csv", parse_dates=["tarih"])
    fig, eksenler = plt.subplots(1, 2, figsize=(13.33, 7.5), sharey=True)
    fig.subplots_adjust(left=0.07, right=0.97, top=0.78, bottom=0.2, wspace=0.06)
    fig.text(0.07, 0.93, "Her taraf kendi tarzında abartıyor ve bu tarz zamanla pek değişmiyor",
             fontsize=19, color=METIN, fontweight="bold")
    fig.text(0.07, 0.885, "Tank + zırhlı araç iddiası ÷ Oryx'in kanıtladığı kayıp (iddiadan 60 gün sonraki sayım). "
             "1× = iddia doğru, altı = eksik sayma.", fontsize=12.5, color=METIN2)
    for ax, savas, edenler in [(eksenler[0], "Rusya-Ukrayna", ["Rusya", "Ukrayna"]),
                               (eksenler[1], "Karabağ 2020", ["Ermenistan", "Azerbaycan"])]:
        sade(ax)
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(kat_fmt)
        ax.set_yticks([0.5, 1, 2, 5, 10])
        ax.grid(axis="y", color=IZGARA, linewidth=0.8)
        ax.axhline(1, color=METIN2, linewidth=1.2)
        ax.set_title(savas, loc="left", fontsize=14, color=METIN, pad=10)
        for e in edenler:
            d = t[(t.iddia_eden == e) & (t.kategori == "zirhli_toplam")].sort_values("tarih")
            ax.plot(d.tarih, d.abartma, "-o", color=RENK[e], linewidth=2, markersize=6 if len(d) < 40 else 3.5,
                    markeredgecolor=ZEMIN, markeredgewidth=1, label=ETIKET[e])
            son = d.iloc[-1]
            ax.annotate(f"{son.abartma:.1f}×", (son.tarih, son.abartma), xytext=(6, 0), textcoords="offset points",
                        va="center", fontsize=12, color=METIN, fontweight="bold")
        ax.legend(loc="upper left", bbox_to_anchor=(0, -0.08), frameon=False, fontsize=11.5, labelcolor=METIN2)
        if savas == "Karabağ 2020":
            ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: matplotlib.dates.num2date(x).strftime("%d.%m")))
            ax.set_xlim(pd.Timestamp("2020-09-24"), pd.Timestamp("2020-12-10"))
        else:
            ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: matplotlib.dates.num2date(x).strftime("%Y")))
            ax.xaxis.set_major_locator(matplotlib.dates.YearLocator())
    eksenler[0].set_ylim(0.3, 14)
    fig.text(0.07, 0.025, "Kaynak: Ukrayna Genelkurmayı, Rusya Savunma Bakanlığı (Telegram), Azerbaycan ve Ermenistan resmi "
             "açıklamaları, Oryx. Dikey eksen logaritmik.", fontsize=10.5, color=METIN2)
    fig.savefig(SONUC / "grafik_6_abartma_zaman.png", dpi=150)
    plt.close(fig)
    print("-> grafik_6_abartma_zaman.png")


def model_sonuclari():
    s = pd.read_csv(KOK / "results/model_sonuclari.csv")
    satirlar = [  # (deney, test_iddia_eden, etiket)
        ("1 Savaşlar arası (R-U ile eğit, Karabağ test)", "Azerbaycan", "Azerbaycan"),
        ("1 Savaşlar arası (R-U ile eğit, Karabağ test)", "Ermenistan", "Ermenistan"),
        ("2 Biri dışarıda: Rusya", "Rusya", "Rusya"),
        ("2 Biri dışarıda: Ukrayna", "Ukrayna", "Ukrayna"),
        ("3 Zaman bölmeli (Tem 2023 öncesiyle eğit, sonrasını test)", "Rusya", "Rusya"),
        ("3 Zaman bölmeli (Tem 2023 öncesiyle eğit, sonrasını test)", "Ukrayna", "Ukrayna"),
        ("4a Karabağ zaman bölmeli (sadece Karabağ, 24 Eki öncesi eğit)", "Azerbaycan", "Azerbaycan"),
        ("4a Karabağ zaman bölmeli (sadece Karabağ, 24 Eki öncesi eğit)", "Ermenistan", "Ermenistan"),
    ]
    modeller = [("B0 Resmi iddia", "Resmi iddiaya inan", "#9a9893", "s"),
                ("B2 Kategori düzeltmesi", "Basit düzeltme (kategori medyanı)", "#2a78d6", "o"),
                ("B3 Tarafın kendi geçmişi", "Basit düzeltme (tarafın kendi geçmişi)", "#1baf7a", "o"),
                ("RF Random Forest", "Random Forest", "#eda100", "D"),
                ("GB Gradient Boosting", "Gradient Boosting", "#eb6834", "D")]
    fig, ax = plt.subplots(figsize=(13.33, 7.5))
    fig.subplots_adjust(left=0.30, right=0.97, top=0.82, bottom=0.18)
    sade(ax)
    fig.text(0.03, 0.93, "Yapay zeka ancak tarafın geçmiş iddialarını gördüğünde işe yarıyor",
             fontsize=19, color=METIN, fontweight="bold")
    fig.text(0.03, 0.885, "Medyan hata: tahmin Oryx'ten tipik olarak kaç kat sapıyor? (1× = mükemmel, sola doğru daha iyi)",
             fontsize=12.5, color=METIN2)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(kat_fmt)
    ax.set_xticks([1, 1.5, 2, 3, 5, 10])
    ax.set_xlim(0.95, 14)
    ax.grid(axis="x", color=IZGARA, linewidth=0.8)
    ax.axvline(1, color=METIN2, linewidth=1.2)
    n = len(satirlar)
    for i, (deney, eden, et) in enumerate(satirlar):
        y = n - 1 - i
        for j, (m, _, renk, isaret) in enumerate(modeller):
            r = s[(s.deney == deney) & (s.test_iddia_eden == eden) & (s.model == m)]
            if r.empty:
                continue
            ax.plot(r.medyan_kat_hata.iloc[0], y + (j - 2) * 0.11, isaret, color=renk, markersize=10,
                    markeredgecolor=ZEMIN, markeredgewidth=1.5, zorder=3)
    ax.set_yticks(range(n))
    ax.set_yticklabels([s_[2] for s_ in reversed(satirlar)], fontsize=13, color=METIN)
    ax.set_ylim(-0.6, n - 0.4)
    for y0, y1, baslik, golge in [(5.5, 7.5, "Hiç görmediği savaş\n(R-U → Karabağ)", False),
                                  (3.5, 5.5, "Hiç görmediği taraf", True),
                                  (1.5, 3.5, "Tarafın geçmişini görmüş\n(R-U, Tem 2023 sonrası)", False),
                                  (-0.5, 1.5, "Tarafın geçmişini görmüş\n(Karabağ, 24 Eki sonrası)", True)]:
        ax.axhspan(y0, y1, color="#f2f1ec" if golge else ZEMIN, zorder=0)
        ax.text(-0.3, (y0 + y1) / 2, baslik, transform=ax.get_yaxis_transform(), ha="left", va="center",
                fontsize=11.5, color=METIN2)
    for _, et, renk, isaret in modeller:
        ax.plot([], [], isaret, color=renk, markersize=9, label=et)
    ax.legend(loc="upper left", bbox_to_anchor=(-0.36, -0.07), ncol=3, frameon=False, fontsize=11, labelcolor=METIN2)
    fig.text(0.03, 0.025, "Test verisi eğitimde hiç kullanılmadı. Karabağ testi 21 iddia, geriye dönük. Kaynak: results/model_sonuclari.csv. Yatay eksen logaritmik.",
             fontsize=10.5, color=METIN2)
    fig.savefig(SONUC / "grafik_7_model_sonuclari.png", dpi=150)
    plt.close(fig)
    print("-> grafik_7_model_sonuclari.png")


if __name__ == "__main__":
    abartma_zaman()
    model_sonuclari()
