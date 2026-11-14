"""
Rusya-Ukrayna: iki tarafın resmi iddiaları vs Oryx (fotoğrafla kanıtlanmış kayıp), kategori kategori.

Girdi : data/clean/model_tablosu.csv (scripts/model_veri_hazirla.py)
Çıktı : results/ru_ua_ozet.csv              (her taraf x kategori: son iddia, Oryx, oran; yıllık medyan oran)
        results/grafik_8_ru_ua_kategoriler.png (6 kategori, abartma oranı zaman içinde, iki taraf)
Oran = iddia / Oryx (iddiadan 60 gün sonraki sayım). Oryx alt sınır olduğu için oran abartmanın üst sınırıdır.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

KOK = Path(__file__).resolve().parent.parent
METIN, METIN2, IZGARA, ZEMIN = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
RENK = {"Ukrayna": "#2a78d6", "Rusya": "#eb6834"}
ETIKET = {"Ukrayna": "Ukrayna'nın iddiası (Rus kayıpları)", "Rusya": "Rusya'nın iddiası (Ukrayna kayıpları)"}
KATLAR = [("zirhli_toplam", "Tank + zırhlı araç"), ("topcu", "Topçu"), ("roketatar", "Çok namlulu roketatar"),
          ("hava_savunma", "Hava savunma"), ("ucak", "Uçak"), ("helikopter", "Helikopter")]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "axes.edgecolor": IZGARA,
                     "xtick.color": METIN2, "ytick.color": METIN2, "axes.facecolor": ZEMIN,
                     "figure.facecolor": ZEMIN, "savefig.facecolor": ZEMIN})


def main():
    t = pd.read_csv(KOK / "data/clean/model_tablosu.csv", parse_dates=["tarih"])
    t = t[t.savas == "Rusya-Ukrayna"].copy()
    t["yil"] = t.tarih.dt.year

    son = t.sort_values("tarih").groupby(["iddia_eden", "kategori"]).tail(1)
    son = son[["iddia_eden", "kayip_taraf", "kategori", "tarih", "iddia", "oryx_hedef", "abartma"]]
    yillik = t.pivot_table(index=["iddia_eden", "kategori"], columns="yil", values="abartma", aggfunc="median")
    yillik.columns = [f"oran_{c}" for c in yillik.columns]
    ozet = son.merge(yillik.reset_index(), on=["iddia_eden", "kategori"])
    ozet = ozet.rename(columns={"tarih": "son_iddia_tarihi", "iddia": "son_iddia", "oryx_hedef": "oryx_60_gun_sonra",
                                "abartma": "son_oran"})
    ozet["oryx_60_gun_sonra"] = ozet.oryx_60_gun_sonra.round(0).astype(int)
    ozet.round({"son_oran": 2, "oran_2022": 2, "oran_2023": 2, "oran_2024": 2, "oran_2025": 2}).sort_values(["kategori", "iddia_eden"]).to_csv(KOK / "results/ru_ua_ozet.csv", index=False)

    fig, eksenler = plt.subplots(2, 3, figsize=(13.33, 7.5), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.06, right=0.95, top=0.82, bottom=0.14, hspace=0.32, wspace=0.12)
    fig.text(0.06, 0.94, "Rusya-Ukrayna: iki taraf da abartıyor, Rusya çoğu kategoride daha fazla",
             fontsize=18, color=METIN, fontweight="bold")
    fig.text(0.06, 0.895, "İddia ÷ Oryx'in fotoğrafla kanıtladığı kayıp (60 gün sonraki sayım). 1× = iddia doğru. "
             "Dikey eksen logaritmik.", fontsize=12, color=METIN2)
    for ax, (kat, baslik) in zip(eksenler.flat, KATLAR):
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.tick_params(length=0)
        ax.set_yscale("log")
        ax.set_yticks([1, 2, 5, 10, 20])
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}×"))
        ax.set_ylim(0.7, 40)
        ax.grid(axis="y", color=IZGARA, linewidth=0.8)
        ax.axhline(1, color=METIN2, linewidth=1)
        ax.set_title(baslik, loc="left", fontsize=13, color=METIN, pad=6)
        sonlar = {}
        for e in ["Rusya", "Ukrayna"]:
            d = t[(t.iddia_eden == e) & (t.kategori == kat)].sort_values("tarih")
            ax.plot(d.tarih, d.abartma, color=RENK[e], linewidth=2, label=ETIKET[e])
            sonlar[e] = d.iloc[-1]
        yakin = max(sonlar["Rusya"].abartma, sonlar["Ukrayna"].abartma) / min(sonlar["Rusya"].abartma, sonlar["Ukrayna"].abartma) < 1.25
        for e, s_ in sonlar.items():
            kay = 0 if not yakin else (7 if s_.abartma >= sonlar["Rusya" if e == "Ukrayna" else "Ukrayna"].abartma else -7)
            ax.annotate(f"{s_.abartma:.1f}×", (s_.tarih, s_.abartma), xytext=(4, kay), textcoords="offset points",
                        va="center", fontsize=11, color=RENK[e], fontweight="bold")
        ax.xaxis.set_major_locator(matplotlib.dates.YearLocator())
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: matplotlib.dates.num2date(x).strftime("%Y")))
    eksenler[0, 0].legend(loc="upper left", bbox_to_anchor=(0, -1.42), ncol=2, frameon=False, fontsize=11.5,
                          labelcolor=METIN2)
    fig.text(0.06, 0.02, "Kaynak: Ukrayna Genelkurmayı (haftalık), Rusya Savunma Bakanlığı Telegram kanalı (haftalık), "
             "Oryx (github.com/scarnecchia/oryx_data). Mart 2022 – Haziran 2025.", fontsize=10, color=METIN2)
    fig.savefig(KOK / "results/grafik_8_ru_ua_kategoriler.png", dpi=150)
    plt.close(fig)
    with pd.option_context("display.width", 220):
        print(ozet.sort_values(["kategori", "iddia_eden"]).to_string(index=False))


if __name__ == "__main__":
    main()
