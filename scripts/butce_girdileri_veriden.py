"""
30 milyar $ senaryosunun hedef sayılarını ve kapasitelerini VERİDEN üretir (önceki elle girilmiş tahminlerin yerine).

Hedef sayıları (bir yılda bulunup vurulabilecek düşman hedefi):
  - Kaynak: Ukrayna Genelkurmayı'nın son 12 aydaki (7 Kas 2025 – 7 Kas 2026) iddia artışı
    (data/raw/ukrayna_gs_iddialari.json).
  - Abartma düzeltmesi: bu projede hesaplanan Ukrayna iddiası / Oryx oranları (results/yillik_artis_oranlari.csv,
    2024-2025 ortalaması). Oranı olmayan kategorilerde zırhlının oranı (3,2) kullanılır.
  - alt  = iddia / oran  (Oryx'in fotoğrafla doğrulayabildiği düzey; gerçek kaybın alt sınırı)
    üst  = iddia x 1,5   (daha fazla mühimmatla vurulabilecek ek hedef payı; VARSAYIM)
    orta = sqrt(alt x iddia)
  - Dron ekibi, mevzi/bina, keşif İHA: Genelkurmay ayrı vermiyor -> önceki varsayımlar korunur.
Tehditler: Şahed tipi 2025'te 54.538 fırlatma (32.200 saldırı tipi; ISIS raporu); balistik füze 2025'te
  ~770 (25 Ekim'e kadar, Zelenski) ve Ekim 2025'te ayda ~148 (CSIS).
Kapasiteler: PAC-3 MSE 2025'te 620 teslimat (Lockheed); GMLRS 14.004/yıl (ABD FY2027 bütçesi), birim ~190.500 $;
  Javelin 3.960/yıl (2026 sonu hedefi); önleyici dron ~1.500/gün (Ara 2025–Oca 2026, Şmıhal) -> ~550 bin/yıl;
  FPV 4 mn (2025); 155 mm 2 mn (ABD+NATO 2025 sonu). Lancet tipi ve güdümlü bomba: VARSAYIM (kaynak yok).
Not: kapasiteler üreticinin TOPLAM üretimidir; tek bir alıcıya hepsinin gitmesi iyimser bir varsayımdır.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
G = KOK / "data/raw/butce_senaryosu"

GS_KOLON = {"tank": "tank", "zirhli": "APC", "topcu": "field artillery", "roketatar": "MRL",
            "hava_savunma": "anti-aircraft warfare", "radar_eh": "special equipment", "lojistik": "vehicles and fuel tanks"}
ORAN_KAT = {"tank": "zirhli_toplam", "zirhli": "zirhli_toplam", "topcu": "topcu", "roketatar": "roketatar",
            "hava_savunma": "hava_savunma"}


def main():
    gs = pd.DataFrame(json.load(open(KOK / "data/raw/ukrayna_gs_iddialari.json")))
    gs["date"] = pd.to_datetime(gs["date"])
    a = gs[gs.date == "2025-11-07"].iloc[0]
    b = gs[gs.date == "2026-11-07"].iloc[0]
    y = pd.read_csv(KOK / "results/yillik_artis_oranlari.csv")
    y = y[(y.iddia_eden == "Ukrayna") & (y.yil.isin([2024, 2025]))].groupby("kategori").artis_orani.mean()
    varsayilan_oran = float(y["zirhli_toplam"])

    h = pd.read_csv(G / "hedefler.csv").set_index("hedef")
    for t, kol in GS_KOLON.items():
        iddia = float(b[kol] - a[kol])
        oran = float(y[ORAN_KAT[t]]) if t in ORAN_KAT else varsayilan_oran
        alt = iddia / oran
        h.loc[t, ["yillik_sayi_dusuk", "yillik_sayi_merkez", "yillik_sayi_yuksek"]] = \
            [round(alt), round(np.sqrt(alt * iddia)), round(1.5 * iddia)]
        h.loc[t, "kaynak"] = (f"VERİ: Ukrayna Genelkurmayı son 12 ay iddiası {iddia:,.0f} ('{kol}', 7 Kas 2025-7 Kas 2026); "
                              f"alt = iddia / {oran:.1f} (bu projenin iddia/Oryx oranı"
                              f"{'' if t in ORAN_KAT else ', zırhlı oranı vekil'}), üst = iddia x 1,5. Değer: birim_maliyetler.csv")
        print(f"{t:13s} iddia {iddia:8,.0f}  oran {oran:5.1f}  ->  alt {alt:8,.0f}  orta {np.sqrt(alt*iddia):8,.0f}  üst {1.5*iddia:8,.0f}")
    h.loc["shahed", ["yillik_sayi_dusuk", "yillik_sayi_merkez", "yillik_sayi_yuksek"]] = [32200, 45000, 130000]
    h.loc["shahed", "kaynak"] = ("VERİ: 2025'te 54.538 Şahed tipi fırlatma, ~32.200'ü saldırı tipi (ISIS raporu); 2026 başında "
                                 "günde 350-500 (Zelenski) -> üst 130 bin. Önlenen hasar değeri: VARSAYIM")
    h.loc["balistik", ["yillik_sayi_dusuk", "yillik_sayi_merkez", "yillik_sayi_yuksek"]] = [770, 1000, 1800]
    h.loc["balistik", "kaynak"] = ("VERİ: 2025'te 25 Ekim'e kadar ~770 balistik füze (Zelenski); Ekim 2025'te ~148/ay (CSIS) -> üst 1.800. "
                                   "Önlenen hasar: Ürdün saldırısı (~85 mn $/geçen füze) üst uç; aralık VARSAYIM")
    h.to_csv(G / "hedefler.csv")

    s = pd.read_csv(G / "silahlar.csv").set_index("silah")
    s.loc["patriot", ["maliyet_dusuk", "maliyet_merkez", "maliyet_yuksek", "yillik_kapasite"]] = [4e6, 5e6, 6.5e6, 620]
    s.loc["patriot", "kaynak"] = ("Kapasite: Lockheed 2025'te 620 PAC-3 MSE teslim etti (tüm müşteriler; 2030'a kadar 2.000 hedefi). "
                                  "Maliyet: 9,8 mrd $ / ~1.970 önleyici sözleşmesi -> ~5 mn $. Başarı ~%90: VARSAYIM")
    s.loc["gmlrs", ["maliyet_dusuk", "maliyet_merkez", "maliyet_yuksek", "yillik_kapasite"]] = [100000, 190000, 200000, 14004]
    s.loc["gmlrs", "kaynak"] = "Kapasite: ABD Ordusu FY2027 bütçesi 14.004/yıl; birim maliyet 190.508 $ (Mart 2025 alımı). Etkinlik: VARSAYIM"
    s.loc["tanksavar", "yillik_kapasite"] = 3960
    s.loc["tanksavar", "kaynak"] = "Kapasite: Javelin 2.400 -> 3.960/yıl (2026 sonu, Lockheed). Maliyet ~175 bin $. Etkinlik: VARSAYIM"
    s.loc["onleyici_dron", ["maliyet_dusuk", "maliyet_merkez", "maliyet_yuksek", "yillik_kapasite"]] = [1000, 2500, 5000, 550000]
    s.loc["onleyici_dron", "kaynak"] = ("Kapasite: Ara 2025-Oca 2026 günde 1.500+ (Şmıhal) -> ~550 bin/yıl. Maliyet: P1-SUN 1.000 $, "
                                        "Sting 2.100-2.500 $, Zelenski 3-5 bin $. Başarı: %68 (Zelenski) - %92 (üretici), hedef başına 2-3 önleyici")
    s.loc["lancet", "kaynak"] = ("Maliyet: ~35.000 $ (Wikipedia), 37-67 bin $ (Gubarev). Etkinlik: imha modeli x 0,35 (yayın sapması). "
                                 "Kapasite 20 bin: VARSAYIM (resmi veri yok; LostArmour'da en yüksek ayda ~285 yayınlanmış saldırı)")
    s.loc["gudumlu_bomba", "kaynak"] = ("Maliyet: kit ~24-25 bin $ + eldeki FAB. Kapasite 30 bin: VARSAYIM (Rusya ayda ~3.500 (2024) -> "
                                        "Ağu 2026'da 8.766 kullandı). Etkinlik: VARSAYIM")
    s.to_csv(G / "silahlar.csv")
    print(s[["maliyet_merkez", "yillik_kapasite"]].to_string())
    print("Maksimum satın alınabilir (kapasite x fiyat): %.1f mrd $" % ((s.maliyet_merkez * s.yillik_kapasite).sum() / 1e9))


if __name__ == "__main__":
    main()
