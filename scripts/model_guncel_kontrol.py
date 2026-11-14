"""
İleriye dönük kontrol: abartma düzeltme modeli, eğitim verisi bittikten ~15 ay sonrasını tutturuyor mu?

Neden ayrı bir betik? Modelin hedefi olan günlük Oryx serisi (github.com/scarnecchia/oryx_data) 21 Ağustos 2025'te
duruyor; bu yüzden ana model (model_egit.py) Haziran 2025 sonrasındaki iddiaları kullanamıyor. İddia verileri ise
Kasım 2026'ya kadar var. Burada Oryx sayfalarının 12 Kasım 2026'daki kategori başlık toplamları tek bir yeni ölçüm
olarak kullanılır (data/raw/oryx_ru_ua_anlik_2026-11-12.csv; sayfalardan okundu, alt toplamlar başlıklarla tutuyor).

Yöntem:
  - Eğitim: model_tablosu.csv'nin tamamı (hedefi bilinen bütün iddialar; son iddia tarihi 20 Haziran 2025).
  - Test  : her iki tarafın, 12 Kasım 2026'dan 60 gün önceki (13 Eylül 2026'ya en yakın) iddiası, 6 kategori.
            Ukrayna: 11 Eylül 2026. Rusya: 20 Ekim 2026 (Telegram verisinde Tem 2025 - Eki 2026 arası toplanmadı).
            Hedef: 12 Kasım 2026 Oryx başlık toplamı. Toplam 12 tahmin (2 taraf x 6 kategori).
  - Tahminciler model_egit.py ile aynı: B0 resmi iddia, B3 tarafın kendi geçmiş medyanı, RF, GB.
Ek: son dönemin (21 Ağu 2025 -> 12 Kas 2026) ARTIŞ bazında abartma oranı (iddia artışı / Oryx artışı).
  Dikkat: Oryx yeni kayıpları gecikmeyle eklediği için son dönem artış oranı yukarı sapmalıdır.

Çıktı: results/model_guncel_kontrol.csv, results/model_guncel_artis_oranlari.csv, results/grafik_15_guncel_kontrol.png
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_egit as me  # noqa: E402
import model_veri_hazirla as mv  # noqa: E402

KOK = me.KOK
ANLIK = pd.Timestamp("2026-11-12")
ONCEKI = pd.Timestamp("2025-08-21")          # günlük Oryx serisinin son günü
ESLE = {
    "zirhli_toplam": ["Armoured Combat Vehicles (Tanks+AFV+IFV+APC+MRAP)"],
    "topcu": ["Towed Artillery", "Self-Propelled Artillery"],
    "roketatar": ["Rocket and Missile Artillery"],
    "hava_savunma": ["Anti-Aircraft Guns", "Self-Propelled Anti-Aircraft Guns", "Surface-To-Air Missile Systems"],
    "ucak": ["Aircraft"],
    "helikopter": ["Helicopters"],
}
AD = {"zirhli_toplam": "Tank + zırhlı", "topcu": "Topçu", "roketatar": "Roketatar", "hava_savunma": "Hava savunma",
      "ucak": "Uçak", "helikopter": "Helikopter"}
METIN, METIN2, IZGARA, ZEMIN = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"


def oryx_anlik():
    a = pd.read_csv(KOK / "data/raw/oryx_ru_ua_anlik_2026-11-12.csv").set_index(["kayip_taraf", "oryx_basligi"]).toplam
    return {(t, k): float(sum(a[(t, b)] for b in bl)) for t in ["Rusya", "Ukrayna"] for k, bl in ESLE.items()}


def iddialar():
    """Bütün tarihlerdeki iddialar + model özellikleri (model_veri_hazirla.main ile aynı tanımlar)."""
    parcalar = []
    for fonk in (mv.ukrayna_iddialari, mv.rusya_iddialari):
        df, bas = fonk()
        df["savas_gunu"] = (df.tarih - bas).dt.days + 1
        parcalar.append(df)
    t = pd.concat(parcalar, ignore_index=True).sort_values(["iddia_eden", "kategori", "tarih"])
    onceki = t.groupby(["iddia_eden", "kategori"])[["iddia", "tarih"]].shift(1)
    gun = (t.tarih - onceki.tarih).dt.days
    t["artis_hizi"] = np.where(gun > 0, np.log(t.iddia / onceki.iddia) / gun * 30, 0.0)
    t["artis_hizi"] = t.artis_hizi.fillna(0.0)
    t["log_gun"] = np.log10(t.savas_gunu)
    for k in me.KATEGORILER:
        t[f"kat_{k}"] = (t.kategori == k).astype(int)
    for e in me.EDENLER:
        t[f"eden_{e}"] = (t.iddia_eden == e).astype(int)
    return t


def main():
    egitim = me.hazirla()
    tum = iddialar()
    oryx = oryx_anlik()
    hedef_gun = ANLIK - mv.GECIKME
    # her (iddia eden, kategori) için 13 Eylül 2026'ya en yakın iddia
    tum["uzaklik"] = (tum.tarih - hedef_gun).abs()
    test = tum.loc[tum.groupby(["iddia_eden", "kategori"]).uzaklik.idxmin()].copy()
    # Rusya'nın Telegram verisinde Tem 2025 - Eki 2026 arası toplanmadı: en yakın iddia 20 Ekim 2026 (60 yerine 23 gün
    # önce). Kümülatif iddia bu 37 günde ~%1,5 arttığı için etkisi küçük.
    assert test.uzaklik.max() <= pd.Timedelta(days=40), test[["iddia_eden", "kategori", "tarih"]]
    test["oryx_hedef"] = [oryx[(k, c)] for k, c in zip(test.kayip_taraf, test.kategori)]
    test["log_abartma"] = np.log10(test.iddia / test.oryx_hedef)

    sonuc, _ = me.tahmin_et(egitim, test, me.KIMLI, kendi_gecmisi=True)
    satir = []
    for model in ["B0 Resmi iddia", "B3 Tarafın kendi geçmişi", "RF Random Forest", "GB Gradient Boosting"]:
        tah = sonuc[model]
        for (_, r), th in zip(test.iterrows(), tah):
            tahmin = r.iddia / 10 ** th
            satir.append({"iddia_eden": r.iddia_eden, "kategori": r.kategori, "iddia_tarihi": r.tarih.date(),
                          "iddia": int(r.iddia), "oryx_12kas2026": int(r.oryx_hedef), "model": model,
                          "tahmin": round(tahmin), "kat_hata": round(10 ** abs(np.log10(tahmin / r.oryx_hedef)), 2),
                          "yon": "fazla" if tahmin > r.oryx_hedef else "eksik"})
    s = pd.DataFrame(satir)
    s.to_csv(KOK / "results/model_guncel_kontrol.csv", index=False)
    ozet = s.groupby(["iddia_eden", "model"]).kat_hata.median().unstack().round(2)
    ozet.loc["İkisi birlikte"] = s.groupby("model").kat_hata.median().round(2)
    print("Eğitim: %d satır, son iddia %s | Test iddiaları: %s .. %s" % (
        len(egitim), egitim.tarih.max().date(), test.tarih.min().date(), test.tarih.max().date()))
    print("Medyan kat hata (12 tahmin):\n", ozet.to_string(), "\n")
    print(s.pivot_table(index=["iddia_eden", "kategori"], columns="model", values="kat_hata").round(2).to_string(), "\n")

    # son dönem artış oranı: 21 Ağu 2025 -> 12 Kas 2026
    eski = mv.ru_ua_oryx()
    art = []
    for eden, kayip in [("Ukrayna", "Rusya"), ("Rusya", "Ukrayna")]:
        for k in me.KATEGORILER:
            g = tum[(tum.iddia_eden == eden) & (tum.kategori == k)].set_index("tarih").iddia.sort_index()
            i0, i1 = mv.deger_al(g, ONCEKI), mv.deger_al(g, ANLIK)
            o0, o1 = mv.deger_al(eski[(kayip, k)], ONCEKI), oryx[(kayip, k)]
            tum_donem = egitim[(egitim.iddia_eden == eden) & (egitim.kategori == k)].abartma.median()
            art.append({"iddia_eden": eden, "kategori": k, "iddia_artisi": int(i1 - i0), "oryx_artisi": int(round(o1 - o0)),
                        "artis_orani": round((i1 - i0) / (o1 - o0), 1) if o1 - o0 >= 5 else np.nan,
                        "kumulatif_oran_kas2026": round(i1 / o1, 1), "egitim_medyani": round(tum_donem, 1)})
    art = pd.DataFrame(art)
    art.to_csv(KOK / "results/model_guncel_artis_oranlari.csv", index=False)
    print(art.to_string(index=False))
    grafik(s)


def grafik(s):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "axes.edgecolor": IZGARA, "xtick.color": METIN2,
                         "ytick.color": METIN2, "axes.facecolor": ZEMIN, "figure.facecolor": ZEMIN, "savefig.facecolor": ZEMIN})
    fig, eksen = plt.subplots(1, 2, figsize=(15, 7.2), sharex=True)
    fig.subplots_adjust(top=0.74, bottom=0.2, left=0.1, right=0.98, wspace=0.32)
    fig.text(0.02, 0.94, "İleriye dönük kontrol: model 15 ay sonrasını tutturuyor mu?", fontsize=18, color=METIN, fontweight="bold")
    fig.text(0.02, 0.885, "Haziran 2025'e kadarki iddialarla eğitildi; Eylül-Ekim 2026 iddiaları düzeltilip 12 Kasım 2026 Oryx sayımıyla "
             "karşılaştırıldı (her tarafta 6 kategori).", fontsize=12, color=METIN2)
    stil = {"B0 Resmi iddia": ("#8f8e88", "o", "Resmi iddia (düzeltme yok)"),
            "B3 Tarafın kendi geçmişi": ("#eb6834", "s", "Tarafın geçmiş ortalamasına böl"),
            "RF Random Forest": ("#2a78d6", "D", "Random Forest"),
            "GB Gradient Boosting": ("#1f9e6e", "^", "Gradient Boosting")}
    kats = list(AD)
    for a, eden in zip(eksen, ["Ukrayna", "Rusya"]):
        d = s[s.iddia_eden == eden]
        for i, k in enumerate(kats):
            dk = d[d.kategori == k].set_index("model")
            a.plot([dk.kat_hata.min(), dk.kat_hata.max()], [i, i], color=IZGARA, lw=5, solid_capstyle="butt", zorder=1)
            for m, (renk, isaret, _) in stil.items():
                a.plot(dk.loc[m, "kat_hata"], i, isaret, color=renk, ms=9, mec=ZEMIN, mew=1.5, zorder=3)
        a.set_xscale("log")
        a.set_xticks([1, 1.5, 2, 3, 5, 10, 20, 40]); a.set_xticklabels(["1", "1,5", "2", "3", "5", "10", "20", "40"])
        a.minorticks_off()
        a.axvline(1, color=METIN2, lw=1)
        a.set_yticks(range(len(kats))); a.set_yticklabels([AD[k] for k in kats]); a.invert_yaxis()
        a.grid(axis="x", color=IZGARA, lw=0.8); a.set_axisbelow(True)
        for sp in ("top", "right", "left"):
            a.spines[sp].set_visible(False)
        a.tick_params(axis="y", length=0)
        med = d.groupby("model").kat_hata.median()
        a.set_title(f"{eden}'nın iddiaları\nmedyan hata: iddia {med['B0 Resmi iddia']:.1f} kat → geçmiş ortalama "
                    f"{med['B3 Tarafın kendi geçmişi']:.2f} · RF {med['RF Random Forest']:.2f} · GB {med['GB Gradient Boosting']:.2f}"
                    .replace(".", ","), loc="left", fontsize=11.5, color=METIN)
        a.set_xlabel("Oryx'ten kaç kat sapıyor (1 = tam isabet, logaritmik)")
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], marker=i, color=r, ls="", ms=9, label=e) for r, i, e in stil.values()],
               ncol=4, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 0.06), fontsize=11)
    fig.text(0.02, 0.015, "Oryx: sayfaların 12 Kasım 2026 kategori başlık toplamları (alt sınır). İddialar: Ukrayna Genelkurmayı, "
             "Rusya Savunma Bakanlığı Telegram. Yalnızca 12 tahmin; tek bir tarihe ait kontrol.", fontsize=9.5, color=METIN2)
    fig.savefig(KOK / "results/grafik_15_guncel_kontrol.png", dpi=150)


if __name__ == "__main__":
    main()
