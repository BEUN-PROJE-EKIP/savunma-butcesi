"""
Kategori tanım/görünürlük farkını ayıklayan normalizasyon.

Sorun: topçuda oranlar 20x-31x, Rusya'nın roketatar oranı 18x. Bunun bir kısmı abartma değil,
"iddia edilen şey" ile "Oryx'in görebildiği şey" arasındaki kategori farkı (ör. dronla vurulan
topçunun çoğu hiç fotoğraflanmıyor). Bu fark iki taraf için de aynı yönde çalışır.

Yöntem (iki yönlü toplamsal model, log ölçekte):
    log10(oran[kategori, taraf]) = a[kategori] + b[taraf] + artık
  a  -> kategori ortak çarpanı: iki tarafa birden etki eden tanım + Oryx görünürlüğü farkı
  b  -> taraf çarpanı: o tarafın kategoriden bağımsız genel abartması
  artık -> o tarafa ÖZGÜ kategori sapması (gerçek "anormallik" budur)
Pratikte: normalize oran = Rusya oranı / Ukrayna oranı (kategori çarpanı sadeleşir).

Ayrıca yıllık ARTIŞ oranları (o yıl eklenen iddia / o yıl eklenen Oryx) hesaplanır;
kategori farkının ne zaman ortaya çıktığını gösterir.

Girdi : results/ru_ua_ozet.csv, data/clean/model_tablosu.csv
Çıktı : results/normalizasyon.csv, results/yillik_artis_oranlari.csv,
        results/grafik_9_normalizasyon.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
METIN, METIN2, IZGARA, ZEMIN = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
RENK = {"Ukrayna": "#2a78d6", "Rusya": "#eb6834"}
KAT_AD = {"zirhli_toplam": "Tank + zırhlı", "topcu": "Topçu", "roketatar": "Roketatar",
          "hava_savunma": "Hava savunma", "ucak": "Uçak", "helikopter": "Helikopter"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "axes.edgecolor": IZGARA,
                     "xtick.color": METIN2, "ytick.color": METIN2, "axes.facecolor": ZEMIN,
                     "figure.facecolor": ZEMIN, "savefig.facecolor": ZEMIN})


def iki_yonlu_model():
    s = pd.read_csv(KOK / "results/ru_ua_ozet.csv")
    p = s.pivot(index="kategori", columns="iddia_eden", values="son_oran")
    L = np.log10(p)
    b = L.mean(axis=0) - L.values.mean()
    a = L.mean(axis=1)
    artik = L - np.add.outer(a.values, b.values)
    genel = 10 ** (b["Rusya"] - b["Ukrayna"])
    t = pd.DataFrame({
        "ham_oran_rusya": p.Rusya.round(2), "ham_oran_ukrayna": p.Ukrayna.round(2),
        "kategori_ortak_carpani": (10 ** a).round(2),
        "normalize_rusya_bolu_ukrayna": (p.Rusya / p.Ukrayna).round(2),
        "rusyaya_ozgu_sapma": (10 ** artik.Rusya).round(2),
    })
    return t, genel


def yillik_artis():
    d = pd.read_csv(KOK / "data/clean/model_tablosu.csv", parse_dates=["tarih"])
    d = d[d.savas != "Karabağ 2020"]
    noktalar = ["2022-12-31", "2023-12-31", "2024-12-31", "2025-06-20"]
    satir = []
    for (e, k), g in d.groupby(["iddia_eden", "kategori"]):
        g = g.sort_values("tarih")
        v = [g.iloc[0]] + [g[g.tarih <= t].iloc[-1] for t in noktalar]
        for i in range(1, len(v)):
            di, do = v[i].iddia - v[i - 1].iddia, v[i].oryx_hedef - v[i - 1].oryx_hedef
            satir.append({"iddia_eden": e, "kategori": k, "yil": v[i].tarih.year,
                          "iddia_artis": int(di), "oryx_artis": round(do, 1),
                          "artis_orani": round(di / do, 1) if do > 0 else np.nan})
    return pd.DataFrame(satir)


def grafik(t, genel, y):
    sira = ["zirhli_toplam", "topcu", "roketatar", "hava_savunma", "ucak", "helikopter"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 6.5), gridspec_kw={"width_ratios": [1.15, 1]})
    fig.subplots_adjust(top=0.80, bottom=0.17, wspace=0.28, left=0.06, right=0.97)
    fig.text(0.06, 0.94, "Topçudaki fark iki tarafta ortak, roketatardaki fark sadece Rusya'da",
             fontsize=18, color=METIN, fontweight="bold")
    fig.text(0.06, 0.885, "Normalize oran = Rusya'nın abartma oranı / Ukrayna'nın abartma oranı. "
             "Kategori tanım/görünürlük farkı iki tarafı da etkilediği için bu bölmede sadeleşir.",
             fontsize=12, color=METIN2)

    x = np.arange(len(sira))
    vals = t.loc[sira, "normalize_rusya_bolu_ukrayna"].values
    a1.bar(x, vals, width=0.55, color=RENK["Rusya"])
    for xi, v in zip(x, vals):
        a1.text(xi, v + 0.12, f"{v:.1f}×", ha="center", fontsize=11, color=METIN)
    a1.axhline(genel, color=METIN2, linewidth=1.5, linestyle="--")
    a1.text(3, genel + 0.12, f"genel ortalama {genel:.1f}×", ha="center",
            fontsize=11, color=METIN2)
    a1.axhline(1, color=METIN2, linewidth=1)
    a1.set_xticks(x, [KAT_AD[k] for k in sira], rotation=20)
    a1.set_ylabel("Rusya oranı / Ukrayna oranı")
    a1.grid(axis="y", color=IZGARA, linewidth=0.8)
    a1.set_axisbelow(True)
    a1.set_title("Normalize edilmiş oran (Haziran 2025)", loc="left", fontsize=13, color=METIN)
    for s in ["top", "right"]:
        a1.spines[s].set_visible(False)

    tp = y[y.kategori == "topcu"]
    yillar = sorted(tp.yil.unique())
    w = 0.38
    for i, e in enumerate(["Ukrayna", "Rusya"]):
        g = tp[tp.iddia_eden == e].set_index("yil").reindex(yillar)
        a2.bar(np.arange(len(yillar)) + (i - 0.5) * w, g.iddia_artis, width=w - 0.03,
               color=RENK[e], label=f"{e}'nın iddiası (yıllık eklenen)")
        a2.plot(np.arange(len(yillar)) + (i - 0.5) * w, g.oryx_artis, "o", color=METIN,
                markersize=8, markeredgecolor=ZEMIN, markeredgewidth=2)
    a2.plot([], [], "o", color=METIN, markersize=8, label="Oryx'in doğruladığı (aynı yıl)")
    a2.set_xticks(np.arange(len(yillar)), [str(v) if v != 2025 else "2025\n(Haz'a kadar)" for v in yillar])
    a2.set_ylabel("Bir yılda eklenen topçu sistemi")
    a2.grid(axis="y", color=IZGARA, linewidth=0.8)
    a2.set_axisbelow(True)
    a2.legend(frameon=False, fontsize=10, loc="upper left", labelcolor=METIN2)
    a2.set_title("Topçu: iki tarafın iddiası 2024'te birlikte patlıyor", loc="left", fontsize=13, color=METIN)
    for s in ["top", "right"]:
        a2.spines[s].set_visible(False)

    fig.text(0.06, 0.03, "Kaynak: Ukrayna Genelkurmayı (PetroIvaniuk veri seti), Rusya Savunma Bakanlığı "
             "(t.me/mod_russia_en), Oryx (github.com/scarnecchia/oryx_data).", fontsize=10, color=METIN2)
    fig.savefig(KOK / "results/grafik_9_normalizasyon.png", dpi=150)


def main():
    t, genel = iki_yonlu_model()
    y = yillik_artis()
    t.to_csv(KOK / "results/normalizasyon.csv")
    y.to_csv(KOK / "results/yillik_artis_oranlari.csv", index=False)
    print(t.to_string())
    print(f"\nRusya/Ukrayna genel taraf farkı: {genel:.2f}x")
    print(y.pivot_table(index=["kategori", "iddia_eden"], columns="yil", values="artis_orani").to_string())
    grafik(t, genel, y)


if __name__ == "__main__":
    main()
