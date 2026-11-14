"""
Yapay zeka modeli: resmi kayıp iddiasından gerçeğe en yakın kaybı (Oryx) tahmin etmek.

Model "abartma oranını" tahmin eder:  log10(iddia / Oryx)
Tahmini gerçek kayıp = iddia / 10^(tahmin edilen log-abartma)

Özellikler (ölçekten bağımsız; iddianın büyüklüğü KULLANILMAZ, çünkü Rusya-Ukrayna'da sayılar binlerle,
Karabağ'da yüzlerle ölçülüyor ve ağaç modeller bu farkı genelleyemiyor - ilk denemede bu yüzden kötü çıktı):
  log_gun     : savaşın kaçıncı günü (log10)
  artis_hizi  : iddianın bir önceki açıklamaya göre aylık log-artışı
  kategori    : zirhli_toplam, topcu, roketatar, hava_savunma, ucak, helikopter (one-hot; iki tarafta aynı)
  eden_*      : iddia sahibi (one-hot) -> sadece Deney 3'te (orada model iddia sahibini eğitimde görmüştür)

Üç deney (hepsinde test verisi eğitimde yoktur):
  1) Savaşlar arası : Rusya-Ukrayna ile eğit -> Karabağ'da test et
  2) Biri dışarıda  : 4 iddia sahibinden birini çıkar, kalan 3 ile eğit, çıkanı tahmin et
  4) Karabağ zaman bölmeli: 24 Ekim 2020 öncesi Karabağ iddialarıyla eğit (a: sadece Karabağ, b: + R-U),
                      sonraki Karabağ iddialarını test et (geriye dönük; test kümesi 21 satır)
  3) Zaman bölmeli  : 1 Temmuz 2023'ten önce doğrulanmış (hedefi bilinen) iddialarla eğit,
                      sonraki Rusya-Ukrayna iddialarını tahmin et. Bir gözlemcinin savaş sürerken
                      yapabileceği şey budur: tarafın geçmiş iddialarını Oryx ile karşılaştırıp
                      yeni iddialarını düzeltmek.
Hata: |log10(tahmin / Oryx)|  ->  "kaç kat yanıldı" = 10^hata. Rapor: medyan kat hata (1.00 = mükemmel).

Tahminciler:
  B0 Resmi iddia          : iddiaya olduğu gibi inan
  B1 Sabit düzeltme       : iddiayı eğitimdeki medyan abartmaya böl
  B2 Kategori düzeltmesi  : iddiayı eğitimde o kategorinin medyan abartmasına böl
  B3 Tarafın kendi geçmişi: iddiayı o tarafın o kategorideki geçmiş medyan abartmasına böl (sadece Deney 3)
  RF Random Forest, GB Gradient Boosting

Çıktılar: results/model_sonuclari.csv, results/model_tahminleri.csv, results/model_ozellik_onemi.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

KOK = Path(__file__).resolve().parent.parent
KATEGORILER = ["zirhli_toplam", "topcu", "roketatar", "hava_savunma", "ucak", "helikopter"]
EDENLER = ["Ukrayna", "Rusya", "Azerbaycan", "Ermenistan"]
OLCEKSIZ = ["log_gun", "artis_hizi"] + [f"kat_{k}" for k in KATEGORILER]
KIMLI = OLCEKSIZ + [f"eden_{e}" for e in EDENLER]
ZAMAN_KESIMI = pd.Timestamp("2023-07-01")
KARABAG_KESIMI = pd.Timestamp("2020-10-24")


def hazirla():
    t = pd.read_csv(KOK / "data/clean/model_tablosu.csv", parse_dates=["tarih", "hedef_tarih"])
    for k in KATEGORILER:
        t[f"kat_{k}"] = (t.kategori == k).astype(int)
    for e in EDENLER:
        t[f"eden_{e}"] = (t.iddia_eden == e).astype(int)
    return t


def agirlik(egitim):
    """Her iddia sahibi eşit ağırlıkta (Ukrayna'nın ~600 satırı Karabağ'ın ~40 satırını ezmesin)"""
    return (1.0 / egitim.groupby("iddia_eden").iddia_eden.transform("size")).values


def agirlikli_medyan(x, w):
    i = np.argsort(x)
    x, w = np.asarray(x)[i], np.asarray(w)[i]
    c = np.cumsum(w)
    return x[np.searchsorted(c, c[-1] / 2)]


def tahmin_et(egitim, test, ozellikler, kendi_gecmisi=False):
    w = agirlik(egitim)
    y = egitim.log_abartma.values
    genel = agirlikli_medyan(y, w)
    sonuc = {"B0 Resmi iddia": np.zeros(len(test)), "B1 Sabit düzeltme": np.full(len(test), genel)}
    kat_med = {k: agirlikli_medyan(y[(egitim.kategori == k).values], w[(egitim.kategori == k).values])
               for k in KATEGORILER if (egitim.kategori == k).any()}
    sonuc["B2 Kategori düzeltmesi"] = test.kategori.map(kat_med).fillna(genel).values
    if kendi_gecmisi:
        ek = egitim.groupby(["iddia_eden", "kategori"]).log_abartma.median()
        e = egitim.groupby("iddia_eden").log_abartma.median()
        sonuc["B3 Tarafın kendi geçmişi"] = np.array(
            [ek.get((a, k), e.get(a, genel)) for a, k in zip(test.iddia_eden, test.kategori)])
    rf = RandomForestRegressor(n_estimators=400, min_samples_leaf=3, random_state=0)
    rf.fit(egitim[ozellikler], y, sample_weight=w)
    gb = GradientBoostingRegressor(n_estimators=300, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=0)
    gb.fit(egitim[ozellikler], y, sample_weight=w)
    sonuc["RF Random Forest"] = rf.predict(test[ozellikler])
    sonuc["GB Gradient Boosting"] = gb.predict(test[ozellikler])
    return sonuc, dict(zip(ozellikler, rf.feature_importances_))


def main():
    t = hazirla()
    deneyler = [("1 Savaşlar arası (R-U ile eğit, Karabağ test)", t.savas == "Rusya-Ukrayna",
                 t.savas == "Karabağ 2020", OLCEKSIZ, False)]
    for e in EDENLER:
        deneyler.append((f"2 Biri dışarıda: {e}", t.iddia_eden != e, t.iddia_eden == e, OLCEKSIZ, False))
    deneyler.append(("3 Zaman bölmeli (Tem 2023 öncesiyle eğit, sonrasını test)", t.hedef_tarih < ZAMAN_KESIMI,
                     (t.savas == "Rusya-Ukrayna") & (t.tarih >= ZAMAN_KESIMI), KIMLI, True))
    # Deney 4: Karabağ kendi içinde. 24 Ekim 2020 öncesi iddialarla eğit (19 satır), sonrasını test et (21 satır).
    # 4a sadece Karabağ verisiyle, 4b buna Rusya-Ukrayna verisi eklenerek.
    # DİKKAT: geriye dönük bir test. Savaş 44 gün sürdüğü için eğitimdeki iddiaların hedefi (60 gün sonraki Oryx)
    # savaş sırasında henüz bilinemezdi; Deney 3'teki gibi "gerçek zamanlı" değil. Test kümesi çok küçük.
    kb = t.savas == "Karabağ 2020"
    deneyler.append(("4a Karabağ zaman bölmeli (sadece Karabağ, 24 Eki öncesi eğit)", kb & (t.tarih < KARABAG_KESIMI),
                     kb & (t.tarih >= KARABAG_KESIMI), KIMLI, True))
    deneyler.append(("4b Karabağ zaman bölmeli (R-U + Karabağ 24 Eki öncesi eğit)",
                     (t.savas == "Rusya-Ukrayna") | (kb & (t.tarih < KARABAG_KESIMI)),
                     kb & (t.tarih >= KARABAG_KESIMI), KIMLI, True))

    satirlar, tahminler, onemler = [], [], []
    for ad, egit_m, test_m, ozl, kendi in deneyler:
        egitim, test = t[egit_m], t[test_m]
        sonuc, onem = tahmin_et(egitim, test, ozl, kendi)
        onemler.append(pd.Series(onem, name=ad))
        for model, tah in sonuc.items():
            hata = pd.Series(np.abs(tah - test.log_abartma.values), index=test.index)
            for eden, h in hata.groupby(test.iddia_eden):
                satirlar.append({"deney": ad, "test_iddia_eden": eden, "model": model, "n": len(h),
                                 "egitim_n": len(egitim), "medyan_kat_hata": round(10 ** h.median(), 2),
                                 "ortalama_log_hata": round(h.mean(), 3)})
            tp = test[["savas", "iddia_eden", "tarih", "kategori", "iddia", "oryx_hedef"]].copy()
            tp["deney"], tp["model"] = ad, model
            tp["tahmin"] = (test.iddia / 10 ** tah).round(1)
            tahminler.append(tp)

    sonuc = pd.DataFrame(satirlar)
    (KOK / "results").mkdir(exist_ok=True)
    sonuc.to_csv(KOK / "results/model_sonuclari.csv", index=False)
    pd.concat(tahminler).to_csv(KOK / "results/model_tahminleri.csv", index=False)
    pd.DataFrame(onemler).round(3).to_csv(KOK / "results/model_ozellik_onemi.csv")
    tablo = sonuc.pivot_table(index=["deney", "test_iddia_eden"], columns="model", values="medyan_kat_hata")
    with pd.option_context("display.width", 250, "display.max_columns", 20):
        print("Medyan kat hata (1.00 = mükemmel; 2.00 = tipik olarak 2 kat yanılıyor)\n")
        print(tablo.to_string())


if __name__ == "__main__":
    main()
