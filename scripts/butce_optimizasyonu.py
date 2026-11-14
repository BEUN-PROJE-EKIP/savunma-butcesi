"""
Maliyet etkinliği ve bütçe dağıtımı (silah-hedef atama).

1) Her hedef türü için bir Lancet'in beklenen getirisi:
       EV(t) = [ P(imha|t) + k * P(hasar|t) ] * V(t)
   P'ler: results/imha_olasiliklari.csv (Random Forest, 2024-2026 güncel dönem; hareketli/duran karışımı
   o hedef türünde gözlenen hareketli payıyla ağırlıklandırılır).
   V(t), Lancet fiyatı ve k (hasarda kaybedilen değer payı): data/raw/silah_hedef/birim_maliyetler.csv.
   Değişim oranı = EV(t) / Lancet fiyatı  ("harcanan 1 $ karşılığı düşmana verilen kayıp $").
   Belirsizlik: fiyatlar ve k, düşük-merkez-yüksek aralığından (log-üçgen) 10.000 kez çekilir (Monte Carlo).

2) Bütçe dağıtımı (doğrusal programlama):
       max  sum_t EV(t) * x_t     s.t.  sum_t x_t <= N  (aynı Lancet sayısı = aynı bütçe),
                                        x_t <= c * gözlenen_t  (bir hedef türünden sınırsız bulunamaz)
   gözlenen_t = 2024-2026'da o hedefe yapılan saldırı sayısı (gerçek dağılım). c = 1,5 ve 2 senaryoları.
   Gerçek dağılımın getirisi ile optimal dağılımın getirisi karşılaştırılır.

Önemli sınırlama: veri yalnızca YAYINLANAN videolardır; gerçek imha oranları daha düşüktür (ıska ve
düşürülen Lancet'ler az görünür). Bu yüzden mutlak değişim oranları üst sınırdır; hedefler arası SIRALAMA
ve dağılım karşılaştırması daha güvenilirdir.

Çıktı: results/maliyet_etkinligi.csv, results/butce_dagilimi.csv, results/grafik_10_butce.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import linprog

KOK = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(0)
N_MC = 10000
AD = {"radar": "Radar", "hs_fuze": "Hava savunma (füze)", "hs_top": "Hava savunma (top)",
      "kundagi_motorlu_top": "Kundağı motorlu top", "cekili_top": "Çekili top", "roketatar": "Roketatar",
      "tank": "Tank", "hafif_zirhli": "Hafif zırhlı", "ozel_arac": "Özel araç", "arac": "Lojistik araç",
      "deniz_araci": "Deniz aracı", "maket": "Maket (yem)"}
METIN, METIN2, IZGARA, ZEMIN = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
RENK_GERCEK, RENK_OPT = "#eb6834", "#2a78d6"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "axes.edgecolor": IZGARA,
                     "xtick.color": METIN2, "ytick.color": METIN2, "axes.facecolor": ZEMIN,
                     "figure.facecolor": ZEMIN, "savefig.facecolor": ZEMIN})


def log_ucgen(dusuk, merkez, yuksek, n):
    return np.exp(RNG.triangular(np.log(dusuk), np.log(merkez), np.log(yuksek), n))


def girdiler():
    m = pd.read_csv(KOK / "data/raw/silah_hedef/birim_maliyetler.csv").set_index("kalem")
    p = pd.read_csv(KOK / "results/imha_olasiliklari.csv")
    d = pd.read_csv(KOK / "data/clean/silah_hedef.csv")
    d = d[(d.kaynak == "LostArmour") & (d.yil >= 2024)]
    gozlenen = d.groupby("hedef_alt").size()
    hareketli_pay = d.groupby("hedef_alt").hareketli.mean()
    hedefler = [h for h in AD if h in m.index and h in set(p.hedef_alt)]
    P = {}
    for h in hedefler:
        a = p[p.hedef_alt == h].set_index("hareketli")
        w = hareketli_pay.get(h, 0)
        P[h] = {k: (1 - w) * a.loc[0, f"p_{k}"] + w * a.loc[1, f"p_{k}"] for k in ("imha", "hasar", "iska")}
    return m, P, gozlenen.reindex(hedefler).fillna(0), hedefler


def main():
    m, P, gozlenen, hedefler = girdiler()
    lancet = log_ucgen(*m.loc["Lancet", ["dusuk_usd", "merkez_usd", "yuksek_usd"]], N_MC)
    k = RNG.triangular(*m.loc["hasar_kayip_orani", ["dusuk_usd", "merkez_usd", "yuksek_usd"]], N_MC)
    satir, EV_merkez = [], {}
    for h in hedefler:
        V = log_ucgen(*m.loc[h, ["dusuk_usd", "merkez_usd", "yuksek_usd"]], N_MC)
        ev = (P[h]["imha"] + k * P[h]["hasar"]) * V
        oran = ev / lancet
        EV_merkez[h] = (P[h]["imha"] + m.loc["hasar_kayip_orani", "merkez_usd"] * P[h]["hasar"]) * m.loc[h, "merkez_usd"]
        satir.append({"hedef_alt": h, "ad": AD[h], "p_imha": round(P[h]["imha"], 3), "p_hasar": round(P[h]["hasar"], 3),
                      "deger_merkez_usd": m.loc[h, "merkez_usd"], "ev_merkez_usd": round(EV_merkez[h]),
                      "oran_medyan": round(np.median(oran), 1), "oran_p10": round(np.percentile(oran, 10), 1),
                      "oran_p90": round(np.percentile(oran, 90), 1), "gozlenen_saldiri_2024_26": int(gozlenen[h])})
    me = pd.DataFrame(satir).sort_values("oran_medyan", ascending=False)
    me.to_csv(KOK / "results/maliyet_etkinligi.csv", index=False)
    print(me.to_string(index=False))

    # --- doğrusal programlama: aynı Lancet sayısıyla en çok beklenen kayıp ---
    N = gozlenen.sum()
    ev = np.array([EV_merkez[h] for h in hedefler])
    gercek_getiri = float((ev * gozlenen.values).sum())
    dag = pd.DataFrame({"hedef_alt": hedefler, "ad": [AD[h] for h in hedefler], "gercek": gozlenen.values.astype(int)})
    ozet = []
    for c in (1.5, 2.0):
        r = linprog(-ev, A_ub=np.ones((1, len(ev))), b_ub=[N],
                    bounds=[(0, c * g) for g in gozlenen.values], method="highs")
        x = r.x
        dag[f"optimal_c{c}"] = np.round(x).astype(int)
        opt_getiri = float(ev @ x)
        # Monte Carlo ile kazancın belirsizliği
        kazanc = []
        for _ in range(500):
            V = np.array([log_ucgen(*m.loc[h, ["dusuk_usd", "merkez_usd", "yuksek_usd"]], 1)[0] for h in hedefler])
            kk = RNG.triangular(0.1, 0.3, 0.5)
            e = np.array([(P[h]["imha"] + kk * P[h]["hasar"]) for h in hedefler]) * V
            rr = linprog(-e, A_ub=np.ones((1, len(e))), b_ub=[N],
                         bounds=[(0, c * g) for g in gozlenen.values], method="highs")
            kazanc.append(float(e @ rr.x) / float(e @ gozlenen.values))
        ozet.append({"senaryo": f"c={c}", "lancet_sayisi": int(N), "gercek_getiri_musd": round(gercek_getiri / 1e6),
                     "optimal_getiri_musd": round(opt_getiri / 1e6), "kat_merkez": round(opt_getiri / gercek_getiri, 2),
                     "kat_p10": round(np.percentile(kazanc, 10), 2), "kat_p90": round(np.percentile(kazanc, 90), 2)})
    dag.to_csv(KOK / "results/butce_dagilimi.csv", index=False)
    oz = pd.DataFrame(ozet)
    oz.to_csv(KOK / "results/butce_ozet.csv", index=False)
    print(dag.to_string(index=False))
    print(oz.to_string(index=False))
    grafik(me, dag, oz)


def grafik(me, dag, oz):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 7.2), gridspec_kw={"width_ratios": [1.1, 1]})
    fig.subplots_adjust(top=0.80, bottom=0.14, left=0.15, right=0.97, wspace=0.55)
    fig.text(0.02, 0.94, "Aynı Lancet bütçesi, hedef seçimiyle çok farklı kayıp verdiriyor",
             fontsize=18, color=METIN, fontweight="bold")
    fig.text(0.02, 0.885, "Sol: harcanan 1 \\$ karşılığı beklenen kayıp (medyan, çubuk = %10-%90). "
             "Sağ: 2024-2026 gerçek hedef dağılımı ile optimal dağılım (aynı sayıda Lancet).",
             fontsize=12, color=METIN2)
    # sol: değişim oranı
    y = np.arange(len(me))[::-1]
    a1.barh(y, me.oran_medyan, height=0.6, color=RENK_OPT)
    a1.errorbar(me.oran_medyan, y, xerr=[me.oran_medyan - me.oran_p10, me.oran_p90 - me.oran_medyan],
                fmt="none", ecolor=METIN2, elinewidth=1.2, capsize=3)
    for yi, v in zip(y, me.oran_medyan):
        a1.text(v * 1.08, yi + 0.28, f"{v:.1f}×".replace(".", ","), fontsize=10, color=METIN)
    a1.set_xscale("log")
    a1.axvline(1, color=METIN2, linewidth=1)
    a1.set_yticks(y, me.ad)
    a1.set_xlabel(r"Kayıp \$ / harcanan \$ (log ölçek)")
    a1.grid(axis="x", color=IZGARA, linewidth=0.8)
    a1.set_axisbelow(True)
    a1.set_title("Hedef türüne göre maliyet etkinliği", loc="left", fontsize=13, color=METIN)
    for s in ["top", "right"]:
        a1.spines[s].set_visible(False)
    # sağ: dağılım (yüzde)
    sira = me.hedef_alt.tolist()
    dd = dag.set_index("hedef_alt").loc[sira]
    y2 = np.arange(len(sira))[::-1]
    h = 0.38
    a2.barh(y2 + h / 2, 100 * dd.gercek / dd.gercek.sum(), height=h - 0.03, color=RENK_GERCEK, label="Gerçek (2024-2026)")
    a2.barh(y2 - h / 2, 100 * dd["optimal_c1.5"] / dd["optimal_c1.5"].sum(), height=h - 0.03, color=RENK_OPT,
            label="Optimal (her hedeften en çok 1,5 kat)")
    a2.set_yticks(y2, dd.ad)
    a2.set_xlabel("Lancet saldırılarının payı (%)")
    a2.grid(axis="x", color=IZGARA, linewidth=0.8)
    a2.set_axisbelow(True)
    a2.legend(frameon=False, fontsize=10, loc="lower right", labelcolor=METIN2)
    k = oz.set_index("senaryo").loc["c=1.5"]
    a2.set_title(f"Optimal dağılım ~{k.kat_merkez:.2f} kat kayıp (%10-%90: {k.kat_p10:.2f}–{k.kat_p90:.2f})".replace(".", ","),
                 loc="left", fontsize=13, color=METIN)
    for s in ["top", "right"]:
        a2.spines[s].set_visible(False)
    fig.text(0.02, 0.02, "Kaynak: LostArmour Lancet tablosu (5.197 videolu saldırı), açık kaynak birim fiyatlar "
             "(birim_maliyetler.csv). Yayınlanan videolar başarıyı abartır: mutlak oranlar üst sınırdır.",
             fontsize=9.5, color=METIN2)
    fig.savefig(KOK / "results/grafik_10_butce.png", dpi=150)


if __name__ == "__main__":
    main()
