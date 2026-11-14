# Karabağ 2020 – Kalabalığın Bilgeliği Projesi

## Klasörler
- data/raw    : ham veriler (değiştirilmez)
- data/clean  : temizlenmiş, analize hazır veriler
- scripts     : veri toplama ve işleme scriptleri
- notebooks   : analiz defterleri
- results     : grafikler, tablolar

## Mevcut veriler
- data/clean/oryx_karabag_ozet.csv : Oryx 2020 Karabağ listesinin özeti (1.933 araç).
  Sütunlar: kayip_taraf, oryx_kategori, proje_kategori, model, oryx_durum,
  durum (imha/hasarli/ele_gecirildi/terk), vuran_silah (TB2/dolanan_muhimmat/Spike_ATGM/belirtilmemis), adet.
  Kaynak: oryxspioenkop.com, 6 Kasım 2026'da okundu.

## Scriptler
- scripts/scrape_oryx.py      : Oryx sayfasını kanıt linkleriyle birlikte kayıt kayıt CSV'ye döker
                                (internet izni gerekir).
- scripts/oryx_ozet_cevir.py  : data/raw/oryx_ozet_kodlu.txt -> data/clean/oryx_karabag_ozet.csv

## Notlar
- Oryx sadece görüntüyle kanıtlanmış kayıpları içerir: gerçek kaybın ALT SINIRIDIR.
- Tanksavar füzeleri, MANPADS ve dolanan mühimmatların kendisi listeye dahil değildir.

- data/clean/oryx_zaman_serisi.csv (+ _genis.csv) : Wayback Machine'deki 31 Oryx kopyasından
  (28 Eyl 2020 – 31 Oca 2021) kategori bazında kümülatif kanıtlanmış kayıplar.
  Script: scripts/oryx_wayback_cevir.py (notlar scriptin başında).
  Önemli: 'TB2 ile vuruldu' etiketleri Ocak 2021 sonrasında eklenmiş; savaş sırasındaki kopyalarda yok.

- data/clean/ucdp_karabag.csv : UCDP GED 26.1'den Azerbaycan–Artsakh çatışmasına ait 128 olay (Eyl–Kas 2020).
  deaths_a = Azerbaycan tarafı, deaths_b = Ermeni/Artsakh tarafı. best/low/high = en iyi tahmin / alt / üst sınır.
  Kaynak dosyadaki bozuk 1 kayıt (id 358948) atlandı.
  Not: id 371976 tüm savaşı kapsayan toplu bir kayıttır (günlük olaylara dağıtılamayan ölümler).

- data/raw/resmi_iddialar.csv : İki tarafın tarihli kümülatif kayıp iddiaları (82 satır, kaynak linkli).
  Ermeni tarafı: Unified Infocenter (7 tarih). Azerbaycan tarafı: MoD ve Aliyev açıklamaları (4 tarih).
- results/iddia_vs_oryx.csv + results/ilk_bulgular.md : iddia / Oryx oranları (o günkü ve nihai).

## GDELT medya verisi ("kalabalık") – 6 Kasım 2026
DURUM: GKG İngilizce + çeviri, saatte 1 dosya çekildi (2.352 dosya, 15.730 makale). Bulgular: results/medya_bulgular.md
GDELT sunucuları Claude'un çalıştığı ortamdan engelli; aşağıdakiler kendi bilgisayarında çalıştırılmalı.
- scripts/gdelt_doc_cek.py      : GDELT DOC 2.0 API -> data/raw/gdelt/doc_makaleler.csv (başlıklar),
                                  doc_hacim.csv (günlük haber hacmi), doc_ton.csv (ortalama ton).
                                  Önce `python scripts/gdelt_doc_cek.py --test` ile API'nin 2020'yi verdiğini kontrol et.
                                  Tüm dönem ~1 saat; yarıda kalırsa tekrar çalıştır, kaldığı yerden devam eder.
- 6 Kas 2026: DOC API bu IP'ye sürekli HTTP 429 veriyor (tarayıcıdan da). Ham dosya sunucusu açık ->
  scripts/gdelt_gkg_indir.py (ÖNERİLEN YOL): 15 dakikalık GKG dosyalarını indirip Karabağ haberlerini süzer
                                  -> data/raw/gdelt/gkg_sayilar.csv + gkg_makaleler.csv. Varsayılan: saatte 1 dosya (~%25 örneklem, ~9 GB).
                                  `--ceviri` İngilizce dışı haberleri de ekler. Yarıda kalırsa kaldığı yerden devam eder.
- scripts/gdelt_gkg_bigquery.sql: GKG'nin metin içinden çıkardığı sayılar (Amounts, V2Counts) için BigQuery sorgusu
                                  (ücretsiz Sandbox). Çıktı -> data/raw/gdelt/gkg_sayilar.csv. Adımlar dosyanın başında.
- scripts/medya_sayi_cikar.py   : başlık + GKG sayılarını (kategori, kayıp tarafı, iddia eden) olarak çıkarır
                                  -> data/clean/medya_iddialari.csv ve results/medya_ozet.csv
                                  (kalabalık medyanı / geometrik ortalama vs resmi iddia vs Oryx).
- Yöntem notu: kalabalık tahmini = her sitenin o kategorideki en büyük sayısının siteler arası medyanı.
  `resmi_ile_ayni` sütunu, medyadaki sayının bir resmi iddiayla birebir aynı olup olmadığını gösterir:
  oran yüksekse medya bağımsız tahmin değil resmi iddianın yankısıdır (kalabalığın bilgeliğinin
  bağımsızlık varsayımı bozulur) – sunumda tartışılmalı.

## Sunum grafikleri (7 Kasım 2026)
- scripts/grafikler.py -> results/grafik_1_ermeni_tank.png, grafik_2_azeri_zirhli.png, grafik_3_azeri_iha.png,
  grafik_4_asker_olu.png, grafik_5_ozet.png (16:9). Resmi iddia (mavi) vs haberlerdeki sayılar (turuncu: iddia eden
  tarafın medyası, gri: diğer) vs Oryx/UCDP (yeşil). Dikey eksenler logaritmik.
- results/_onizleme/ : kontrol için alınmış ara kopyalar, silinebilir.

## Yapay zeka modeli: iddiadan gerçek kaybı tahmin (8 Kasım 2026) — bulgular: results/model_bulgular.md
İkinci savaş olarak Rusya-Ukrayna eklendi (iki tarafın iddiaları da var, tek taraflı değil).
- data/raw/ukrayna_gs_iddialari.json   : Ukrayna Genelkurmayı günlük Rus kayıp iddiaları
                                         (github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset; haftada bir örneklendi)
- data/raw/rusya_mod_telegram.csv      : Rusya Savunma Bak. kümülatif Ukrayna kayıp iddiaları, 182 tarih (~haftalık,
                                         Mar 2022 – Haz 2025), Bakanlığın Telegram kanalından (t.me/mod_russia_en/<id>).
- data/raw/rusya_mod_iddialari.csv     : aynı iddiaların TASS'tan elle derlenen 21 tarihi (doğrulama; ortak günlerde birebir aynı).
- data/raw/oryx_ru_ua_kayitlar.csv     : Oryx R-U kayıt kayıt (github.com/scarnecchia/oryx_data, 2022-03 – 2025-08)
- data/raw/oryx_ru_ua_gunluk_toplam.csv: Oryx'in kendi başlık toplamları (kalibrasyon için)
- scripts/oryx_ru_ua_kategori.py -> data/clean/oryx_ru_ua_zaman_serisi.csv (sistem adından kategori)
- scripts/model_veri_hazirla.py  -> data/clean/model_tablosu.csv (2.141 iddia; hedef = 60 gün sonraki Oryx;
                                    iki taraf da haftalık ve aynı 6 kategori: tank+zırhlı, topçu, roketatar, hava savunma, uçak, helikopter)
                                    + data/clean/oryx_ru_ua_kalibrasyon.csv
- scripts/model_egit.py          -> results/model_sonuclari.csv, model_tahminleri.csv, model_ozellik_onemi.csv
                                    (Random Forest + Gradient Boosting, 3 deney; gerekli: pip install scikit-learn)
- scripts/model_grafikleri.py    -> results/grafik_6_abartma_zaman.png, grafik_7_model_sonuclari.png
Özet: Model hiç görmediği bir tarafın iddiasını düzeltemiyor (abartma tarafa özgü), ama tarafın geçmiş
iddialarını görünce sonrakileri iyi düzeltiyor (Ukrayna 2,5 -> 1,21 kat GB, Rusya 6,2 -> 1,16 kat RF; 8 Kas, haftalık + eşit kategoriler).
Deney 4 (8 Kas): Karabağ kendi içinde, 24 Eki 2020 öncesiyle eğit -> sonrası test (23 iddia, geriye dönük):
Ermenistan 12,2 -> 1,21 kat, Azerbaycan 1,5 -> 1,13 kat (Gradient Boosting).

## Rusya-Ukrayna karşılaştırması (8 Kasım 2026) — ayrıntı: results/ru_ua_bulgular.md
- scripts/ru_ua_karsilastirma.py -> results/ru_ua_ozet.csv, results/grafik_8_ru_ua_kategoriler.png
- İki taraf da abartıyor: Ukrayna Oryx'in ~2–3×, Rusya ~5–6× (zırhlı, uçak, helikopter); roketatar Rusya 17,9× / Ukrayna 2,8×;
  hava savunma eşit (~2,5×). Topçu iki tarafta 20–30× ama büyük ölçüde tanım farkı (havanlar).

## Silah -> hedef -> sonuç verisi (9 Kasım 2026) — bütçe sorusu için
Amaç: taraftan bağımsız olarak "hangi silah türü hangi hedefi ne sonuçla vurdu" tablosu; sonra imha olasılığı
modeli ve maliyet etkinliğine göre bütçe dağıtımı.
- data/raw/silah_hedef/lancet_saldirilari.csv : LostArmour Lancet tablosu (lostarmour.info/lancet), 5.197 videolu
                                               saldırı, Tem 2022 – 3 Kas 2026. Etiketler: hedef türü, sonuç
                                               (уничтожен/поврежден/промах/неизвестен), model, hareketli hedef.
                                               Kaynak Rusya yanlısı; sadece yayınlanan videolar -> başarılar fazla temsil edilir.
- scripts/silah_hedef_hazirla.py -> data/clean/silah_hedef.csv (Lancet + Oryx Karabağ'da vuran silahı belli
                                    669 kayıt: TB2 548, dolanan mühimmat 72, Spike 49; Oryx'te ıska yok)
- LostArmour FPV sayfası (97.962 kayıt) yapılandırılmış sonuç alanı içermiyor ve 4.899 sayfa; alınmadı.
- Bilinen sapma: "neyle vuruldu" bilgisi en çok dronlarda var (dron kendi vuruşunu çeker); topçu/mayın az kayıtlı.
- scripts/imha_modeli.py        -> results/imha_modeli_sonuclari.csv, imha_olasiliklari.csv
                                   (Lancet sonucu imha/hasar/ıska; RF/GB/lojistik vs baseline; zaman bölmeli + 5 katlı CV)
- data/raw/silah_hedef/birim_maliyetler.csv : silah ve hedef birim fiyat aralıkları (kaynaklı; VARSAYIM işaretli)
- scripts/butce_optimizasyonu.py -> results/maliyet_etkinligi.csv, butce_dagilimi.csv, butce_ozet.csv,
                                   grafik_10_butce.png (Monte Carlo + doğrusal programlama ile hedef seçimi)
- Bulgular: results/butce_bulgular.md
- data/raw/silah_hedef/iran_abd_kayiplar.csv : CRS IN12692 (5 Eki 2026) 81 ABD uçağı; neden, silah türü, hasar payı,
                                               yerine koyma maliyeti (CBO/basın). Dost ateşi/kaza/kendi imhası HARIC işaretli.
- scripts/uc_savas_karsilastirma.py -> data/clean/silah_hedef_deger.csv, results/uc_savas_ozet.csv,
                                       results/grafik_11_uc_savas.png (Karabağ + Lancet + İran-ABD: silah -> hedef -> kayıp değeri)
- data/raw/silah_hedef/lostarmour_diger_silahlar.csv : LostArmour silah sayfalarındaki videolu yayın başlıkları (9 Kas 2026,
            tarayıcıyla sayfa sayfa): UMPK 3.801, FPV 1.960 (97.962 kaydın 50 sayfada bir örneklemi), dronla bomba bırakma 1.598,
            helikopter füzesi 356, LMUR 318, Inokhodets 150, KUB 67. LostArmour kayıp listelerinde (/pvo vb.) "neyle vuruldu" alanı yok.
- scripts/rus_silahlari_hedef.py -> data/clean/rus_silah_hedef.csv, results/silah_hedef_karisimi.csv,
            results/grafik_12_silah_karisimi.png (hedef türü başlıktan anahtar kelimeyle; + Lancet + Ukrayna SBS ilk yıl özeti)

## 30 milyar $ bütçe senaryosu (9 Kasım 2026)
- data/raw/butce_senaryosu/silahlar.csv, etkinlik_matrisi.csv, hedefler.csv, etkinlik_notlari.md : 8 silah/savunma
  seçeneğinin fiyat, yıllık üretim kapasitesi, atış başına etkinlik; hedef sayıları ve değerleri (kaynaklı; VARSAYIM işaretli)
- scripts/butce_30_milyar.py -> results/butce_30mlr_dagilim.csv (Monte Carlo), butce_30mlr_senaryolar.csv (A-D senaryoları),
  butce_30mlr_egri.csv (bütçe-getiri eğrisi), grafik_13_butce_30mlr.png. Doğrusal programlama (scipy HiGHS), ~30 sn.
- Bulgular: results/butce_bulgular.md bölüm 6

### 30 milyar $ senaryosu: girdilerin veriden üretilmesi ve duyarlılık
- `scripts/butce_girdileri_veriden.py`: hedef sayılarını Ukrayna GS son 12 ay iddiası / projenin abartma oranlarıyla
  (alt), iddia x1,5 (üst) ve geometrik ortalama (orta) olarak hesaplar; üretim kapasitelerini kaynaklı değerlerle
  günceller. `data/raw/butce_senaryosu/hedefler.csv` ve `silahlar.csv`'yi yeniden yazar. Önce bu, sonra
  `scripts/butce_30_milyar.py` çalıştırılır.
- Yeni çıktı: `results/butce_30mlr_duyarlilik.csv` (tornado). Bulgular: `results/butce_bulgular.md` bölüm 6.

### Kısıtlı bütçe (6 ve 10 milyar $) ve verimlilik eşiği
- `scripts/butce_10_milyar.py`: aynı modelle 6 ve 10 mrd $ dağılımı; son 1 $'ın getirisinin 1'in altına düştüğü
  "verimlilik eşiği" (ikiye bölme ile) ve 2.000 çekilişlik Monte Carlo (~3 dk). `--sadece-grafik` ile Monte Carlo atlanır.
- Çıktılar: `results/butce_10mlr_senaryolar.csv`, `butce_10mlr_esik.csv`, `butce_10mlr_montecarlo.csv`,
  `grafik_14_butce_10mlr.png`. Bulgular: `results/butce_bulgular.md` bölüm 7.
