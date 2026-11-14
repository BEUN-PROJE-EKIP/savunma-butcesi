"""
İmha olasılığı modeli: bir Lancet saldırısının sonucu ne olur?

Veri : data/clean/silah_hedef.csv (kaynak = LostArmour; sonucu belli olanlar: imha / hasar / iska)
Hedef: 3 sınıf (imha, hasar, iska) -> olasılıklar.
Girdi: hedef türü (alt tür), Lancet modeli, hareketli hedef, yıl.
Test 1: zaman bölmeli — 2022-2024 ile eğit, 2025-2026'yı tahmin et (gelecek tahmini).
Test 2: 5 katlı çapraz doğrulama (aynı dönem içinde; yıl girdi olarak var).
Not  : 2025 sonrası "sonuç bilinmiyor" oranı %42-63'e çıkıyor ve hedef bazında imha oranları yıllara göre
       değişiyor (tank 2023 %12 -> 2026 %44); zaman bölmeli testte bu kayma baskın.
Ölçüt: log-loss (olasılığın kalitesi) ve imha için Brier skoru; baseline'larla karşılaştırma:
  B0 = tüm eğitimdeki genel oranlar, B1 = hedef türüne göre oranlar (basit tablo).
Çıktı: results/imha_modeli_sonuclari.csv, results/imha_olasiliklari.csv (son model, tüm veriyle eğitilmiş)
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from sklearn.model_selection import StratifiedKFold

KOK = Path(__file__).resolve().parent.parent
SINIF = ["imha", "hasar", "iska"]


def veri():
    d = pd.read_csv(KOK / "data/clean/silah_hedef.csv")
    d = d[(d.kaynak == "LostArmour") & d.sonuc.isin(SINIF) & (d.hedef != "belirsiz")].copy()
    d["model_kod"] = d.silah_alt.str.replace("Lancet-", "", regex=False)
    d["model_kod"] = d.model_kod.where(d.model_kod.isin(["51", "52", "x51", "x52", "yeni"]), "diger")
    return d


def ozellik(d, sutunlar=None):
    X = pd.get_dummies(d[["hedef_alt", "model_kod"]].astype(str))
    X["hareketli"] = d.hareketli.fillna(0).values
    for y in range(2023, 2027):
        X[f"yil_{y}"] = (d.yil.values == y).astype(float)
    if sutunlar is not None:
        X = X.reindex(columns=sutunlar, fill_value=0)
    return X.astype(float)


def oran_tahmini(egit, test, anahtar=None):
    """Baseline: eğitimdeki sınıf oranları (anahtar verilirse o gruba göre, +1 düzeltmeli)."""
    genel = egit.sonuc.value_counts(normalize=True).reindex(SINIF, fill_value=0)
    if anahtar is None:
        return np.tile(genel.values, (len(test), 1))
    tab = egit.groupby(anahtar).sonuc.value_counts().unstack(fill_value=0).reindex(columns=SINIF, fill_value=0)
    tab = (tab + genel.values * 3).div(tab.sum(1) + 3, axis=0)  # küçük gruplar genele çekilir
    return np.vstack([tab.loc[k].values if k in tab.index else genel.values for k in test[anahtar]])


def degerlendir(ad, y, P):
    P = np.clip(P, 1e-6, 1)
    P = P / P.sum(1, keepdims=True)
    return {"model": ad, "log_loss": round(log_loss(y, P, labels=SINIF), 4),
            "brier_imha": round(brier_score_loss((y == "imha").astype(int), P[:, 0]), 4),
            "dogruluk": round(accuracy_score(y, np.array(SINIF)[P.argmax(1)]), 3)}


def modeller():
    return {
        "Lojistik regresyon": LogisticRegression(max_iter=2000, C=1.0),
        "Random Forest": RandomForestClassifier(n_estimators=400, min_samples_leaf=10, random_state=0),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=200, max_depth=2, learning_rate=0.05,
                                                        subsample=0.8, random_state=0),
    }


def main():
    d = veri()
    egit, test = d[d.yil <= 2024], d[d.yil >= 2025]
    print(f"Eğitim {len(egit)} (2022-2024), test {len(test)} (2025-2026)")
    sonuc = [degerlendir("B0 Genel oran", test.sonuc.values, oran_tahmini(egit, test)),
             degerlendir("B1 Hedef türü oranı", test.sonuc.values, oran_tahmini(egit, test, "hedef_alt"))]
    Xe = ozellik(egit)
    Xt = ozellik(test, Xe.columns)
    for ad, m in modeller().items():
        m.fit(Xe, egit.sonuc)
        P = pd.DataFrame(m.predict_proba(Xt), columns=m.classes_)[SINIF].values
        sonuc.append(degerlendir(ad, test.sonuc.values, P))
    for r in sonuc:
        r["test"] = "zaman (2025-26)"
    # Test 2: çapraz doğrulama
    kf = StratifiedKFold(5, shuffle=True, random_state=0)
    cv = {ad: [] for ad in ["B0 Genel oran", "B1 Hedef türü oranı", *modeller()]}
    y_all, P_all = [], {ad: [] for ad in cv}
    for i_e, i_t in kf.split(d, d.sonuc):
        e, t = d.iloc[i_e], d.iloc[i_t]
        y_all.append(t.sonuc.values)
        P_all["B0 Genel oran"].append(oran_tahmini(e, t))
        P_all["B1 Hedef türü oranı"].append(oran_tahmini(e, t, "hedef_alt"))
        Xe2 = ozellik(e)
        Xt2 = ozellik(t, Xe2.columns)
        for ad, m in modeller().items():
            m.fit(Xe2, e.sonuc)
            P_all[ad].append(pd.DataFrame(m.predict_proba(Xt2), columns=m.classes_)[SINIF].values)
    y_all = np.concatenate(y_all)
    for ad in cv:
        r = degerlendir(ad, y_all, np.vstack(P_all[ad]))
        r["test"] = "5 katlı CV"
        sonuc.append(r)
    s = pd.DataFrame(sonuc)
    s.to_csv(KOK / "results/imha_modeli_sonuclari.csv", index=False)
    print(s.to_string(index=False))

    # son model: tüm veriyle Random Forest (CV'de en iyi Brier) -> hedef başına güncel olasılık
    X = ozellik(d)
    m = RandomForestClassifier(n_estimators=400, min_samples_leaf=10, random_state=0).fit(X, d.sonuc)
    satir = []
    for (h, alt), g in d.groupby(["hedef", "hedef_alt"]):
        for hv in (0, 1):
            # güncel dönem: 2024-2026 tahminlerinin ortalaması (2026'da ıskalar az kaydedilmiş, tek yıl yanıltır)
            ornek = pd.DataFrame({"hedef_alt": [alt] * 3, "model_kod": ["yeni"] * 3, "hareketli": [hv] * 3,
                                  "yil": [2024, 2025, 2026]})
            p = pd.DataFrame(m.predict_proba(ozellik(ornek, X.columns)), columns=m.classes_)[SINIF].mean()
            satir.append({"hedef": h, "hedef_alt": alt, "hareketli": hv, "n_gozlem": len(g),
                          **{f"p_{k}": round(p[k], 3) for k in SINIF}})
    o = pd.DataFrame(satir)
    o.to_csv(KOK / "results/imha_olasiliklari.csv", index=False)
    print(o[o.hareketli == 0].sort_values("p_imha", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
