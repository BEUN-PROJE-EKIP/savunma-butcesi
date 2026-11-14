"""
Senaryo: Rusya-Ukrayna benzeri bir kara savaşında, bir tarafın 1 yıllık 30 milyar $ mühimmat + hava savunma
bütçesini silah türleri arasında en iyi şekilde dağıtması.

Amaç (en büyükle):  düşmana verilen ekipman kaybı ($) + kendi tarafımızda önlenen hasar ($)
Karar değişkeni   :  s[w,t] = w silahıyla t hedefine yapılan atış sayısı
Kısıtlar          :  sum c_w * s[w,t] <= B                       (bütçe)
                     sum_t s[w,t] <= kapasite_w                   (yıllık üretim)
                     sum_w p[w,t] * s[w,t] <= N_t                 (bir yılda vurulabilecek hedef / gelen tehdit sayısı)
Çözüm             :  doğrusal programlama (scipy linprog, HiGHS).
Belirsizlik       :  maliyet, etkinlik, hedef sayısı ve değer aralıklarından 2.000 Monte Carlo çekilişi
                     (log-üçgen / üçgen); her çekilişte optimizasyon yeniden çözülür.

Girdiler (data/raw/butce_senaryosu/): silahlar.csv, etkinlik_matrisi.csv, hedefler.csv — kaynaklar ve
VARSAYIM işaretleri dosyalarda. Lancet etkinliği bu projenin imha modelinden (imha + 0,3 x hasar), yayın sapması
için düşürülebilir. İnsan kaybı parayla ölçülmedi (piyade hedefi yok).
Bu bir karar-destek SENARYOSUDUR, gerçek bir bütçe önerisi değildir.

Çıktı: results/butce_30mlr_dagilim.csv (Monte Carlo özeti), results/butce_30mlr_egri.csv (bütçeye göre dağılım),
       results/grafik_13_butce_30mlr.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import linprog

KOK = Path(__file__).resolve().parent.parent
GIRDI = KOK / "data/raw/butce_senaryosu"
RNG = np.random.default_rng(42)
B = 30e9
N_MC = 2000
METIN, METIN2, IZGARA, ZEMIN = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
RENK = {"fpv": "#2a78d6", "lancet": "#eb6834", "top_mermisi": "#1f9e6e", "gudumlu_bomba": "#8a5cd6",
        "gmlrs": "#d6a21f", "tanksavar": "#c23b5a", "onleyici_dron": "#3fb6c8", "patriot": "#6b6a64"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "axes.edgecolor": IZGARA,
                     "xtick.color": METIN2, "ytick.color": METIN2, "axes.facecolor": ZEMIN,
                     "figure.facecolor": ZEMIN, "savefig.facecolor": ZEMIN})


def oku():
    s = pd.read_csv(GIRDI / "silahlar.csv").set_index("silah")
    p = pd.read_csv(GIRDI / "etkinlik_matrisi.csv").set_index("silah")
    h = pd.read_csv(GIRDI / "hedefler.csv").set_index("hedef")
    return s, p.loc[s.index, h.index], h


def log_ucgen(d, m, y):
    return float(np.exp(RNG.triangular(np.log(d), np.log(m), np.log(y))))


SENARYOLAR = {
    "A: Veriden orta değer": {},
    "B: Hedef sayısı alt sınır (Oryx düzeyi)": {"N_sec": "yillik_sayi_dusuk"},
    "C: Hedef sayısı üst sınır (iddia x 1,5)": {"N_sec": "yillik_sayi_yuksek"},
    "D: C + üretim kapasitesi 3 kat": {"N_sec": "yillik_sayi_yuksek", "kap_carpan": 3.0},
}


def uygula(senaryo, s, P, N, h=None):
    s = s.copy(); P = P.copy(); N = N.copy()
    if "N_sec" in senaryo:
        N = h[senaryo["N_sec"]].astype(float)
    if "fpv_kap" in senaryo:
        s.loc["fpv", "yillik_kapasite"] = senaryo["fpv_kap"]
    if "fpv_etk" in senaryo:
        P.loc["fpv"] *= senaryo["fpv_etk"]
    if "kap_carpan" in senaryo:
        s["yillik_kapasite"] = s["yillik_kapasite"] * senaryo["kap_carpan"]
    if "N_carpan" in senaryo:
        N = N * senaryo["N_carpan"]
    return s, P, N


def cek(s, p, h, merkez=False):
    """Bir parametre seti: merkez=True ise orta değerler."""
    if merkez:
        c = s.maliyet_merkez.astype(float)
        carp = pd.Series(1.0, index=s.index)
        N = h.yillik_sayi_merkez.astype(float)
        V = h.deger_merkez.astype(float)
    else:
        c = pd.Series({w: log_ucgen(*s.loc[w, ["maliyet_dusuk", "maliyet_merkez", "maliyet_yuksek"]]) for w in s.index})
        carp = pd.Series({w: RNG.triangular(s.loc[w, "etkinlik_carpani_dusuk"], 1.0, s.loc[w, "etkinlik_carpani_yuksek"])
                          for w in s.index})
        N = pd.Series({t: RNG.triangular(*h.loc[t, ["yillik_sayi_dusuk", "yillik_sayi_merkez", "yillik_sayi_yuksek"]])
                       for t in h.index})
        V = pd.Series({t: log_ucgen(*h.loc[t, ["deger_dusuk", "deger_merkez", "deger_yuksek"]]) for t in h.index})
    P = p.mul(carp, axis=0).clip(upper=0.95)
    return c, P, N, V


def coz(s, c, P, N, V, butce):
    cift = [(w, t) for w in P.index for t in P.columns if P.loc[w, t] > 0]
    n = len(cift)
    # küçük maliyet cezası: aynı getiriyi veren çözümlerden en ucuzunu seçer (bütçe dolmadıysa artan para boşta kalır)
    amac = -np.array([P.loc[w, t] * V[t] - 1e-3 * c[w] for w, t in cift])
    A, b = [], []
    A.append([c[w] for w, t in cift]); b.append(butce)
    for w0 in P.index:
        A.append([1.0 if w == w0 else 0.0 for w, t in cift]); b.append(s.loc[w0, "yillik_kapasite"])
    for t0 in P.columns:
        A.append([P.loc[w, t] if t == t0 else 0.0 for w, t in cift]); b.append(N[t0])
    r = linprog(amac, A_ub=np.array(A), b_ub=np.array(b), bounds=[(0, None)] * n, method="highs")
    x = pd.Series(r.x, index=pd.MultiIndex.from_tuples(cift, names=["silah", "hedef"]))
    harcama = x.groupby(level=0).sum() * c
    harcama = harcama.reindex(P.index, fill_value=0)
    getiri = float(sum(P.loc[w, t] * V[t] * xi for (w, t), xi in zip(cift, r.x)))
    golge = -r.ineqlin.marginals[0]  # bütçenin gölge fiyatı: son 1 $'ın getirisi
    return x, harcama, getiri, golge


def main():
    s0, p, h = oku()
    s = s0
    # 1) merkez senaryo
    c, P, N, V = cek(s, p, h, merkez=True)
    x, harc, getiri, golge = coz(s, c, P, N, V, B)
    oldurulen = (x * pd.Series({(w, t): P.loc[w, t] for w, t in x.index})).groupby(level=1).sum()
    print("MERKEZ: getiri %.1f mrd $, son 1 $'ın getirisi %.2f $" % (getiri / 1e9, golge))
    print((harc / 1e9).round(2).to_string())
    print("Hedef bazında vurulan/önlenen (merkez):")
    print(pd.DataFrame({"vurulan": oldurulen.round(0), "mevcut": N}).to_string())
    # 2) Monte Carlo
    paylar, getiriler, kullanilan = [], [], []
    for _ in range(N_MC):
        c, P, N, V = cek(s, p, h)
        _, hr, g, _ = coz(s, c, P, N, V, B)
        paylar.append(hr / B)
        getiriler.append(g)
        kullanilan.append(hr.sum())
    M = pd.DataFrame(paylar)
    oz = pd.DataFrame({
        "ad": s.ad, "rol": s.rol,
        "merkez_harcama_mrd": (harc / 1e9).round(2),
        "pay_medyan_%": (100 * M.median()).round(1),
        "pay_p10_%": (100 * M.quantile(0.10)).round(1),
        "pay_p90_%": (100 * M.quantile(0.90)).round(1),
        "secilme_olasiligi_%": (100 * (M > 0.005).mean()).round(0),
    }).sort_values("pay_medyan_%", ascending=False)
    oz.to_csv(KOK / "results/butce_30mlr_dagilim.csv")
    print(oz.to_string())
    ku = np.array(kullanilan) / 1e9
    print("Kullanılan bütçe (Monte Carlo) medyan %.1f mrd $, %%10-%%90: %.1f-%.1f; 30 mrd'nin tamamı kullanılan çekiliş: %%%.0f" % (
        np.median(ku), np.percentile(ku, 10), np.percentile(ku, 90), 100 * (ku > 29.5).mean()))
    oz.attrs["kullanilan"] = (np.median(ku), np.percentile(ku, 10), np.percentile(ku, 90), 100 * (ku > 29.5).mean())
    print("Toplam getiri (Monte Carlo) medyan %.0f mrd $, %%10-%%90: %.0f-%.0f" % (
        np.median(getiriler) / 1e9, np.percentile(getiriler, 10) / 1e9, np.percentile(getiriler, 90) / 1e9))
    # 3) senaryolar: 30 mrd $ dağılımı ve bütçe-getiri eğrisi (merkez parametreler)
    c0, P0, N0, V = cek(s0, p, h, merkez=True)
    dag, egri = {}, []
    for ad, sen in SENARYOLAR.items():
        ss, P, N = uygula(sen, s0, P0, N0, h)
        _, hr, g, gl = coz(ss, c0, P, N, V, B)
        dag[ad] = hr / 1e9
        print(f"{ad}: kullanılan {hr.sum()/1e9:.1f} mrd $, getiri {g/1e9:.1f} mrd $, son 1 $ getirisi {gl:.2f}")
        for bb in np.arange(0.5, 60.5, 0.5) * 1e9:
            _, hr2, g2, gl2 = coz(ss, c0, P, N, V, bb)
            egri.append({"senaryo": ad, "butce_mrd": bb / 1e9, "kullanilan_mrd": hr2.sum() / 1e9, "getiri_mrd": g2 / 1e9,
                         "son_dolar_getirisi": gl2, **(hr2 / 1e9).round(3).to_dict()})
    dag = pd.DataFrame(dag)
    dag.loc["(harcanmayan)"] = 30 - dag.sum()
    dag.round(2).to_csv(KOK / "results/butce_30mlr_senaryolar.csv")
    print(dag.round(2).to_string())
    eg = pd.DataFrame(egri)
    eg.to_csv(KOK / "results/butce_30mlr_egri.csv", index=False)
    tor = tornado(s0, p, h)
    grafik(dag, eg, s0, tor)


def tornado(s0, p, h):
    """Tek seferde bir varsayımı değiştir: 30 mrd $'ın ne kadarı kullanılıyor?"""
    c0, P0, N0, V0 = cek(s0, p, h, merkez=True)
    _, hr, _, _ = coz(s0, c0, P0, N0, V0, B)
    taban = hr.sum() / 1e9
    satir = []
    def kullan(s_=None, c_=None, P_=None, N_=None, V_=None):
        _, hr2, _, _ = coz(s0 if s_ is None else s_, c0 if c_ is None else c_, P0 if P_ is None else P_,
                           N0 if N_ is None else N_, V0 if V_ is None else V_, B)
        return hr2.sum() / 1e9
    for w in s0.index:
        lo = s0.copy(); lo.loc[w, "yillik_kapasite"] *= 0.5
        hi = s0.copy(); hi.loc[w, "yillik_kapasite"] *= 2
        satir.append({"varsayim": f"{s0.loc[w, 'ad'].split(' (')[0]} kapasitesi x0,5 / x2", "dusuk": kullan(s_=lo), "yuksek": kullan(s_=hi)})
    satir.append({"varsayim": "Hedef sayıları alt / üst sınır", "dusuk": kullan(N_=h.yillik_sayi_dusuk.astype(float)),
                  "yuksek": kullan(N_=h.yillik_sayi_yuksek.astype(float))})
    satir.append({"varsayim": "Tüm etkinlikler x0,5 / x2", "dusuk": kullan(P_=(P0 * 0.5)), "yuksek": kullan(P_=(P0 * 2).clip(upper=0.95))})
    satir.append({"varsayim": "Tüm fiyatlar düşük / yüksek uç", "dusuk": kullan(c_=s0.maliyet_dusuk.astype(float)),
                  "yuksek": kullan(c_=s0.maliyet_yuksek.astype(float))})
    satir.append({"varsayim": "Hedef değerleri düşük / yüksek uç", "dusuk": kullan(V_=h.deger_dusuk.astype(float)),
                  "yuksek": kullan(V_=h.deger_yuksek.astype(float))})
    t = pd.DataFrame(satir)
    t["etki"] = (t.yuksek - t.dusuk).abs()
    t = t.sort_values("etki")
    t.attrs["taban"] = taban
    t.to_csv(KOK / "results/butce_30mlr_duyarlilik.csv", index=False)
    print("Duyarlılık (kullanılan mrd $, taban %.1f):" % taban)
    print(t.round(1).to_string(index=False))
    return t


def grafik(dag, eg, s, tor):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 8), gridspec_kw={"width_ratios": [1.1, 1]})
    fig.subplots_adjust(top=0.76, bottom=0.17, left=0.22, right=0.98, wspace=0.28)
    fig.text(0.02, 0.94, "30 milyar $: bu 8 silah için bir yılda harcanabilir mi?", fontsize=18, color=METIN, fontweight="bold")
    fig.text(0.02, 0.885, "Hedef sayıları Ukrayna Genelkurmayı'nın son 12 ayından ve bu projenin abartma oranlarından; kapasitelerin "
             "6/8'i üretici ve bütçe kaynaklarından.", fontsize=12, color=METIN2)
    taban = tor.attrs["taban"]
    y = np.arange(len(tor))
    for yi, (_, r) in zip(y, tor.iterrows()):
        a1.plot([r.dusuk, r.yuksek], [yi, yi], color=IZGARA, linewidth=6, solid_capstyle="butt", zorder=1)
        a1.plot([r.dusuk], [yi], "o", color="#eb6834", markersize=8, zorder=2)
        a1.plot([r.yuksek], [yi], "o", color="#2a78d6", markersize=8, zorder=2)
    a1.axvline(taban, color=METIN2, linewidth=1)
    a1.axvline(30, color=METIN, linewidth=1.2, linestyle="--")
    a1.text(30, len(tor) - 0.4, r"30 mrd \$", ha="right", fontsize=10, color=METIN)
    a1.text(taban, -1.0, f"orta değer: {taban:.1f} mrd \\$".replace(".", ","), ha="center", fontsize=10, color=METIN2)
    a1.set_yticks(y, tor.varsayim, fontsize=10)
    a1.set_ylim(-1.4, len(tor) - 0.2)
    a1.set_xlim(0, 32)
    a1.set_xlabel(r"30 mrd \$'ın kullanılabilen kısmı (milyar \$)")
    a1.grid(axis="x", color=IZGARA, linewidth=0.8)
    a1.set_axisbelow(True)
    a1.plot([], [], "o", color="#eb6834", label="düşük uç (x0,5 / alt sınır)")
    a1.plot([], [], "o", color="#2a78d6", label="yüksek uç (x2 / üst sınır)")
    a1.legend(frameon=False, fontsize=9.5, loc="lower right", labelcolor=METIN2)
    a1.set_title("Hangi varsayım sonucu değiştiriyor?", loc="left", fontsize=13, color=METIN)
    for sp in ["top", "right"]:
        a1.spines[sp].set_visible(False)
    renk_sen = ["#2a78d6", "#eb6834", "#1f9e6e", "#8a5cd6"]
    for sd, rk in zip(dag.columns, renk_sen):
        e = eg[eg.senaryo == sd]
        a2.plot(e.butce_mrd, e.kullanilan_mrd, color=rk, linewidth=2.2, label=sd)
    a2.plot([0, 40], [0, 40], color=IZGARA, linewidth=1, linestyle=":")
    a2.text(33, 31, "verilen bütçenin\ntamamı", fontsize=9, color=METIN2)
    a2.axvline(30, color=METIN, linewidth=1.2, linestyle="--")
    a2.set_xlim(0, 60); a2.set_ylim(0, 45)
    a2.set_xlabel("Verilen bütçe (milyar $)")
    a2.set_ylabel("Anlamlı şekilde harcanan (milyar $)")
    a2.grid(color=IZGARA, linewidth=0.8)
    a2.set_axisbelow(True)
    a2.legend(frameon=False, fontsize=9.5, loc="upper left", labelcolor=METIN2)
    a2.set_title("Senaryolar: para nerede tükenmiyor?", loc="left", fontsize=13, color=METIN)
    for sp in ["top", "right"]:
        a2.spines[sp].set_visible(False)
    fig.text(0.02, 0.03, "Girdiler: data/raw/butce_senaryosu/ (scripts/butce_girdileri_veriden.py ile veriden üretildi). Etkinlik değerleri "
             "VARSAYIM (etkinlik_notlari.md). İnsan kaybı parayla ölçülmedi.\nKapasiteler üreticilerin TOPLAM üretimi; "
             "hepsini tek alıcının alması iyimser. Karar-destek senaryosudur.", fontsize=9.5, color=METIN2)
    fig.savefig(KOK / "results/grafik_13_butce_30mlr.png", dpi=150)


if __name__ == "__main__":
    main()
