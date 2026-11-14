# Savaş verisinden savunma bütçesi — Yapay Zeka dersi projesi

Soru: savaş verilerinden yola çıkarak bir yapay zeka, savunma bütçesini silah türleri arasında nasıl dağıtmalı?

Zincir (her adım bir sonrakine veri verir):
1. **İddialar ne kadar doğru?** Rusya ve Ukrayna'nın resmi kayıp iddiaları, fotoğrafla kanıtlanmış kayıplarla (Oryx)
   karşılaştırılır; Random Forest / Gradient Boosting abartmayı düzeltmeyi öğrenir.
2. **Hangi silah neyi vuruyor?** LostArmour (Lancet + diğer silahlar), Oryx Karabağ 2020 ve İran-ABD 2026
   kayıtlarından silah → hedef → sonuç tablosu; imha olasılığı ve maliyet etkinliği.
3. **Bütçe nasıl dağıtılmalı?** Doğrusal programlama + Monte Carlo + duyarlılık analizi (30, 10 ve 6 milyar $).

Bulguların tamamı: `results/model_bulgular.md`, `results/ru_ua_bulgular.md`, `results/butce_bulgular.md`.

## Klasörler
- `data/raw`    : ham veriler (elle değiştirilmez)
- `data/clean`  : betiklerin ürettiği temiz tablolar
- `scripts`     : bütün betikler (aşağıdaki sırayla çalışır)
- `results`     : grafikler, sonuç tabloları, bulgu dosyaları
- `arsiv`       : projenin ilk aşaması (Karabağ medya analizi, "kalabalığın bilgeliği"). Son zincirde
                  kullanılmıyor; ayrıntı `arsiv/README.md`.

## Veriler (data/raw)
| Dosya | İçerik | Kaynak |
|---|---|---|
| `ukrayna_gs_iddialari.json` | Ukrayna Genelkurmayı günlük kayıp iddiaları, Şub 2022 – 7 Kas 2026 | github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset |
| `rusya_mod_telegram.csv` | Rusya Savunma Bak. raporlarının toplam satırı; Mar 2022 – Haz 2025 haftalık + Eki-Kas 2026'dan 3 rapor | t.me/mod_russia_en |
| `rusya_mod_iddialari.csv` | TASS'tan elle derlenen 21 açıklama (yalnızca doğrulama için) | TASS |
| `oryx_ru_ua_kayitlar.csv`, `oryx_ru_ua_gunluk_toplam.csv` | Oryx Rusya-Ukrayna kayıplarının günlük kazınması; 21 Ağu 2025'te bitiyor | github.com/scarnecchia/oryx_data |
| `oryx_ru_ua_anlik_2026-11-12.csv` | Oryx sayfalarının 12 Kas 2026 kategori başlık toplamları | oryxspioenkop.com |
| `resmi_iddialar.csv` | Karabağ 2020: iki tarafın tarihli resmi iddiaları (modelin 1. ve 4. deneyleri için) | kaynak linkleri dosyada |
| `oryx_ozet_kodlu.txt`, `oryx_wayback_kodlu.txt` | Oryx Karabağ listesi ve Wayback Machine kopyaları | oryxspioenkop.com |
| `silah_hedef/lancet_saldirilari.csv` | 5.197 videolu Lancet saldırısı (hedef, tarih, sonuç) | lostarmour.info |
| `silah_hedef/lostarmour_diger_silahlar.csv` | 8.250 kayıt: güdümlü bomba, FPV (örneklem), dronla bomba, helikopter füzesi, LMUR… | lostarmour.info |
| `silah_hedef/iran_abd_kayiplar.csv` | İran-ABD 2026: 81 ABD hava aracı kaybı/hasarı | CRS IN12692 |
| `silah_hedef/birim_maliyetler.csv` | Silah ve hedeflerin fiyat aralıkları | kaynaklar dosyada |
| `butce_senaryosu/silahlar.csv` | 8 silah: fiyat, yıllık üretim kapasitesi | kaynaklar dosyada; Lancet ve güdümlü bomba kapasitesi VARSAYIM |
| `butce_senaryosu/hedefler.csv` | Hedef türleri: yıllık sayı (alt/orta/üst), değer | `butce_girdileri_veriden.py` üretir |
| `butce_senaryosu/etkinlik_matrisi.csv` | Silah x hedef başarı olasılığı | gerekçeler `etkinlik_notlari.md`; Lancet dışında çoğu VARSAYIM |

## Betikler (çalıştırma sırası)
Gerekenler: Python 3, pandas, numpy, scikit-learn, scipy, matplotlib.

**Adım 1 – abartma**
1. `oryx_ru_ua_kategori.py` → `data/clean/oryx_ru_ua_zaman_serisi.csv`
2. `scrape_oryx.py`, `oryx_ozet_cevir.py`, `oryx_wayback_cevir.py` → Karabağ Oryx tabloları (`oryx_karabag_ozet.csv`, `oryx_zaman_serisi.csv`)
3. `model_veri_hazirla.py` → `data/clean/model_tablosu.csv` (2.141 iddia; hedef = 60 gün sonraki Oryx)
4. `model_egit.py` → `results/model_sonuclari.csv`, `model_tahminleri.csv`, `model_ozellik_onemi.csv`
5. `model_grafikleri.py` → grafik 6, 7 · `ru_ua_karsilastirma.py` → grafik 8, `ru_ua_ozet.csv`
6. `normalizasyon.py` → grafik 9, `yillik_artis_oranlari.csv` (bütçe modelindeki hedef sayıları bu oranları kullanır)
7. `model_guncel_kontrol.py` → grafik 15, `model_guncel_kontrol.csv` (12 Kas 2026 Oryx sayımıyla ileriye dönük kontrol)

**Adım 2 – silah → hedef**
1. `silah_hedef_hazirla.py` → `data/clean/silah_hedef.csv` (Lancet + Oryx Karabağ)
2. `imha_modeli.py` → `results/imha_olasiliklari.csv`, `imha_modeli_sonuclari.csv`
3. `butce_optimizasyonu.py` → grafik 10, `maliyet_etkinligi.csv` (Lancet maliyet etkinliği ve yeniden dağıtım)
4. `uc_savas_karsilastirma.py` → grafik 11 · `rus_silahlari_hedef.py` → grafik 12, `silah_hedef_karisimi.csv`

**Adım 3 – bütçe**
1. `butce_girdileri_veriden.py` → `hedefler.csv` ve `silahlar.csv`'yi veriden yeniden yazar
2. `butce_30_milyar.py` → grafik 13, `butce_30mlr_*.csv` (30 mrd $ + duyarlılık)
3. `butce_10_milyar.py` → grafik 14, `butce_10mlr_*.csv` (6 ve 10 mrd $, verimlilik eşiği; ~3 dk, `--sadece-grafik` ile kısa)

## Grafikler (results)
| No | Konu |
|---|---|
| 6 | Abartma oranının zamanla değişimi |
| 7 | Abartma düzeltme modeli sonuçları |
| 8 | Rusya-Ukrayna: kategori bazında iddia / Oryx |
| 9 | Yıllık artış bazında abartma oranları |
| 10 | Lancet maliyet etkinliği ve yeniden dağıtım |
| 11 | Üç savaş karşılaştırması |
| 12 | Her silah türünün vurduğu hedef karışımı |
| 13 | 30 milyar $ senaryosu ve duyarlılık |
| 14 | 6 ve 10 milyar $, verimlilik eşiği |
| 15 | Modelin ileriye dönük kontrolü (Kasım 2026) |
(1–5 arşivde.)

## Bilinen sınırlar
- Oryx yalnızca görüntüyle kanıtlanmış kayıpları sayar: gerçek kaybın ALT sınırıdır.
- LostArmour Rus tarafı bir kaynaktır ve yalnızca yayınlanan videoları içerir (başarılar fazla temsil edilir).
- Atış başına sonuç verisi yalnızca Lancet için var; diğer silahların etkinliği kalibre edilmiş varsayımdır.
- Günlük Oryx serisi Ağustos 2025'te bittiği için abartma modeli Haziran 2025'e kadarki iddialarla eğitilir.
- İnsan kaybı parayla ölçülmedi. Bütçe sonucu bir karar-destek senaryosudur, gerçek bütçe önerisi değildir.
