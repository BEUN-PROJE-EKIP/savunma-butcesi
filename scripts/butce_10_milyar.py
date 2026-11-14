"""
Kısıtlı bütçe: 30 mrd $ yerine 6 ve 10 mrd $.
Aynı model (scripts/butce_30_milyar.py: doğrusal programlama, aynı girdiler), iki soru:
  1) 10 mrd $ ("askerî ihtiyaç" bütçesi) ve 6 mrd $ ile en iyi silah karışımı ne?
  2) Verimlilik eşiği: bütçenin hangi noktasından sonra son 1 $ düşmana 1 $'dan az ekipman kaybı verdiriyor?
     (LP'nin bütçe gölge fiyatı < 1). Değer yalnızca ekipman fiyatı; piyade bastırma, can kaybı önleme vb.
     parasal olmayan etkiler modelde yok — eşikten sonraki harcamanın gerekçesi bunlar olabilir.
Monte Carlo: 2.000 çekiliş (fiyat, etkinlik, hedef sayısı, değer belirsizliği), 10 mrd $ ile ve eşik için.

Çıktı: results/butce_10mlr_senaryolar.csv, butce_10mlr_esik.csv, butce_10mlr_montecarlo.csv,
       results/grafik_14_butce_10mlr.png
Karar-destek senaryosudur, gerçek bütçe önerisi değildir.
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import butce_30_milyar as m  # noqa: E402

KOK = m.KOK
BUTCELER = [6e9, 10e9]
N_MC = 2000


def esik(s, c, P, N, V, hi=40e9, tol=0.05e9):
    """Son 1 $ getirisinin 1'in altına düştüğü bütçe (gölge fiyat bütçeyle azalır -> ikiye bölme)."""
    _, _, _, g = m.coz(s, c, P, N, V, tol)
    if g < 1:
        return 0.0
    lo = tol
    _, _, _, g = m.coz(s, c, P, N, V, hi)
    if g >= 1:
        return hi
    while hi - lo > tol:
        mid = (lo + hi) / 2
        _, _, _, g = m.coz(s, c, P, N, V, mid)
        lo, hi = (mid, hi) if g >= 1 else (lo, mid)
    return (lo + hi) / 2


def main():
    s0, p, h = m.oku()
    c0, P0, N0, V = m.cek(s0, p, h, merkez=True)

    # 1) senaryolar x bütçeler
    satir, esikler, egri = [], [], []
    for ad, sen in m.SENARYOLAR.items():
        ss, P, N = m.uygula(sen, s0, P0, N0, h)
        e = esik(ss, c0, P, N, V)
        _, hr_e, g_e, _ = m.coz(ss, c0, P, N, V, e)
        _, hr_tum, g_tum, _ = m.coz(ss, c0, P, N, V, 60e9)
        esikler.append({"senaryo": ad, "verimlilik_esigi_mrd": round(e / 1e9, 2),
                        "esikteki_getiri_mrd": round(g_e / 1e9, 1),
                        "doyma_butcesi_mrd": round(hr_tum.sum() / 1e9, 2), "doymadaki_getiri_mrd": round(g_tum / 1e9, 1)})
        for B in BUTCELER:
            _, hr, g, gl = m.coz(ss, c0, P, N, V, B)
            satir.append({"senaryo": ad, "butce_mrd": B / 1e9, "harcanan_mrd": round(hr.sum() / 1e9, 2),
                          "getiri_mrd": round(g / 1e9, 1), "getiri_kat": round(g / hr.sum(), 1),
                          "son_dolar_getirisi": round(gl, 2), **(hr / 1e9).round(2).to_dict()})
        for bb in np.arange(0.1, 15.01, 0.1) * 1e9:
            _, hr2, g2, gl2 = m.coz(ss, c0, P, N, V, bb)
            egri.append({"senaryo": ad, "butce_mrd": bb / 1e9, "getiri_mrd": g2 / 1e9, "son_dolar_getirisi": gl2})
    sen = pd.DataFrame(satir)
    es = pd.DataFrame(esikler)
    eg = pd.DataFrame(egri)
    sen.to_csv(KOK / "results/butce_10mlr_senaryolar.csv", index=False)
    es.to_csv(KOK / "results/butce_10mlr_esik.csv", index=False)
    print(es.to_string(index=False))
    print(sen.to_string(index=False))

    if "--sadece-grafik" in sys.argv:
        grafik(eg, es, sen, s0); return
    # 2) Monte Carlo: 10 mrd $ dağılımı + eşik dağılımı
    m.RNG = np.random.default_rng(42)
    paylar, esk, getiri10, getiri_esik, baglayici = [], [], [], [], []
    for _ in range(N_MC):
        c, P, N, Vv = m.cek(s0, p, h)
        _, hr, g, gl = m.coz(s0, c, P, N, Vv, 10e9)
        paylar.append(hr / 1e9)
        getiri10.append(g)
        baglayici.append(hr.sum() > 9.95e9)
        e = esik(s0, c, P, N, Vv)
        esk.append(e / 1e9)
        _, _, ge, _ = m.coz(s0, c, P, N, Vv, e) if e > 0 else (None, None, 0.0, None)
        getiri_esik.append(ge)
    M = pd.DataFrame(paylar)
    esk = np.array(esk)
    mc = pd.DataFrame({
        "ad": s0.ad,
        "harcama_medyan_mrd": M.median().round(2),
        "harcama_p10_mrd": M.quantile(0.10).round(2),
        "harcama_p90_mrd": M.quantile(0.90).round(2),
        "secilme_olasiligi_%": (100 * (M > 0.05).mean()).round(0),
    }).sort_values("harcama_medyan_mrd", ascending=False)
    ozet = {
        "10 mrd tamamen harcanan çekiliş %": round(100 * np.mean(baglayici), 1),
        "eşik medyan mrd": round(float(np.median(esk)), 2),
        "eşik p10 mrd": round(float(np.percentile(esk, 10)), 2),
        "eşik p90 mrd": round(float(np.percentile(esk, 90)), 2),
        "eşik < 10 mrd olan çekiliş %": round(100 * float(np.mean(esk < 10)), 1),
        "10 mrd getiri medyan mrd": round(float(np.median(getiri10)) / 1e9, 1),
        "eşikteki getirinin 10 mrd getirisine oranı medyan %": round(
            100 * float(np.median(np.array(getiri_esik) / np.array(getiri10))), 1),
    }
    for k, v in ozet.items():
        mc.loc["_" + k, "ad"] = f"{k}: {v}"
    mc.to_csv(KOK / "results/butce_10mlr_montecarlo.csv")
    print(mc.to_string())
    grafik(eg, es, sen, s0)


def grafik(eg, es, sen, s):
    fig = plt.figure(figsize=(17, 10.5))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.6, 1], width_ratios=[1, 1.15], hspace=0.12, wspace=0.42,
                          top=0.80, bottom=0.20, left=0.06, right=0.985)
    a1 = fig.add_subplot(gs[0, 0]); a2 = fig.add_subplot(gs[1, 0], sharex=a1); a3 = fig.add_subplot(gs[:, 1])
    fig.text(0.02, 0.945, "Kısıtlı bütçe: 6 ve 10 milyar \\$ nereye gitmeli?", fontsize=18, color=m.METIN, fontweight="bold")
    A = "A: Veriden orta değer"
    eA = float(es.set_index("senaryo").loc[A, "verimlilik_esigi_mrd"])
    fig.text(0.02, 0.895, f"Orta senaryoda ilk ~{eA:.1f} mrd \\$'ın her doları 1 \\$'dan fazla ekipman kaybı verdiriyor; "
             "sonrası ekipman değeriyle ölçülünce 1 \\$'dan az.".replace(".", ",", 1), fontsize=12, color=m.METIN2)
    d = eg[eg.senaryo == A]
    for a in (a1, a2):
        a.axvspan(0, eA, color="#1f9e6e", alpha=0.07, lw=0)
        a.axvline(eA, color="#1f9e6e", lw=1.5, ls="--")
        a.axvline(10, color=m.METIN, lw=1.2, ls=":")
        a.grid(color=m.IZGARA, lw=0.8); a.set_axisbelow(True)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    a1.plot(d.butce_mrd, d.getiri_mrd, color="#2a78d6", lw=2)
    a1.set_ylabel("Toplam getiri (milyar \\$)")
    a1.set_title("Orta senaryo (A): bütçe arttıkça getiri", loc="left", fontsize=13, color=m.METIN)
    a1.set_ylim(0, d.getiri_mrd.max() * 1.15)
    a1.text(eA - 0.2, 4, f"verimlilik eşiği\n~{eA:.1f} mrd \\$".replace(".", ","), ha="right", fontsize=10, color="#1f9e6e")
    a1.text(10.2, 4, "10 mrd \\$", ha="left", fontsize=10, color=m.METIN)
    plt.setp(a1.get_xticklabels(), visible=False)
    a2.step(d.butce_mrd, d.son_dolar_getirisi.clip(upper=8), where="post", color="#eb6834", lw=2)
    a2.axhline(1, color=m.METIN2, lw=1)
    a2.text(14.9, 1.25, "1 \\$ harca = 1 \\$ kayıp verdir", ha="right", fontsize=9.5, color=m.METIN2)
    a2.set_ylabel("Son 1 \\$'ın getirisi (\\$)")
    a2.set_xlabel("Bütçe (milyar \\$)")
    a2.set_xlim(0, 15); a2.set_ylim(0, 8.5)

    # sağ: senaryo x bütçe yığılmış yatay çubuk
    sira = ["patriot", "onleyici_dron", "fpv", "lancet", "gudumlu_bomba", "gmlrs", "tanksavar", "top_mermisi"]
    kisa = {"A: Veriden orta değer": "A: orta", "B: Hedef sayısı alt sınır (Oryx düzeyi)": "B: az hedef",
            "C: Hedef sayısı üst sınır (iddia x 1,5)": "C: bol hedef", "D: C + üretim kapasitesi 3 kat": "D: bol hedef + 3 kat üretim"}
    etiket, y = [], []
    yy = 0
    for ad in kisa:
        for B in (6, 10):
            r = sen[(sen.senaryo == ad) & (sen.butce_mrd == B)].iloc[0]
            sol = 0
            for w in sira:
                v = r[w]
                if v > 0.005:
                    a3.barh(yy, v, left=sol, color=m.RENK[w], height=0.72, edgecolor=m.ZEMIN, linewidth=2)
                    if v >= 0.75:
                        a3.text(sol + v / 2, yy, f"{v:.1f}".replace(".", ","), ha="center", va="center", fontsize=9, color="white")
                    sol += v
            if B - sol > 0.05:
                a3.barh(yy, B - sol, left=sol, color="none", height=0.72, edgecolor=m.METIN2, linewidth=1, hatch="///")
            a3.text(B + 0.15, yy, f"getiri {r.getiri_mrd:.0f} mrd \\$ ({r.getiri_kat:.1f}x)".replace(".", ","),
                    va="center", fontsize=9.5, color=m.METIN2)
            etiket.append(f"{kisa[ad]} · {B} mrd \\$"); y.append(yy)
            yy += 1
        yy += 0.6
    a3.set_yticks(y); a3.set_yticklabels(etiket, fontsize=10.5)
    a3.invert_yaxis()
    a3.set_xlim(0, 14.5)
    a3.set_xlabel("Harcama (milyar \\$)")
    a3.set_title("Senaryoya göre en iyi karışım", loc="left", fontsize=13, color=m.METIN)
    a3.grid(axis="x", color=m.IZGARA, lw=0.8); a3.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        a3.spines[sp].set_visible(False)
    a3.tick_params(axis="y", length=0)
    from matplotlib.patches import Patch
    h_ = [Patch(color=m.RENK[w], label=s.loc[w, "ad"].split(" (")[0]) for w in sira]
    h_.append(Patch(facecolor="none", edgecolor=m.METIN2, hatch="///", label="harcanmayan (hedef yok)"))
    fig.legend(handles=h_, ncol=5, fontsize=10, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 0.055))
    fig.text(0.02, 0.012, "Getiri = düşmana verilen ekipman kaybı + önlenen hasar ($). Piyade bastırma ve can kaybı önleme parasal "
             "olarak ölçülmedi; eşikten sonraki harcamanın gerekçesi bunlar.\nGirdiler: data/raw/butce_senaryosu/ "
             "(etkinlik değerleri VARSAYIM). Karar-destek senaryosudur.", fontsize=9.5, color=m.METIN2)
    fig.savefig(KOK / "results/grafik_14_butce_10mlr.png", dpi=150)


if __name__ == "__main__":
    main()
