# Yapay zeka modeli: resmi iddiadan gerçek kaybı tahmin etmek (8 Kasım 2026)

## Soru
Bir taraf "X tank vurduk" dediğinde gerçek kayıp ne kadardır? Gerçek kayıp yerine elimizdeki en iyi ölçü
Oryx (fotoğrafla kanıtlanmış kayıp, alt sınır) kullanıldı.

## Veri (data/clean/model_tablosu.csv, 2.141 satır)
| Savaş | İddia eden | Kayıp tarafı | Satır | Dönem | Kaynak |
|---|---|---|---|---|---|
| Karabağ 2020 | Azerbaycan | Ermenistan | 14 | 3 Eki – 1 Ara 2020 | data/raw/resmi_iddialar.csv |
| Karabağ 2020 | Ermenistan | Azerbaycan | 26 | 28 Eyl – 8 Kas 2020 | data/raw/resmi_iddialar.csv |
| Rusya-Ukrayna | Ukrayna Genelkurmayı | Rusya | 1.043 | Şub 2022 – Haz 2025 (haftada bir) | github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset |
| Rusya-Ukrayna | Rusya Savunma Bak. | Ukrayna | 1.058 | Mar 2022 – Haz 2025 (182 tarih, ~haftalık) | Bakanlığın Telegram kanalı t.me/mod_russia_en: data/raw/rusya_mod_telegram.csv |

- Kategoriler (dört tarafta aynı 6): tank+zırhlı, topçu, roketatar, hava savunma, uçak, helikopter.
  Ayrı "tank" kategorisi yok: Rusya tankları ayrı vermiyor ("tanks and other armoured fighting vehicles").
  İki taraf da haftada bir örneklendi (Ukrayna 174, Rusya 182 tarih).
- Hedef: iddia tarihinden **60 gün sonraki** Oryx sayısı (Oryx fotoğraflar ortaya çıktıkça gecikmeli ekliyor).
- Rusya-Ukrayna Oryx serisi: github.com/scarnecchia/oryx_data (Oryx'in günlük kazınması, 2022-03 – 2025-08).
  Kayıtlar sistem adından kategorilere ayrıldı (scripts/oryx_ru_ua_kategori.py) ve Oryx'in kendi başlık
  toplamlarına kalibre edildi (data/clean/oryx_ru_ua_kalibrasyon.csv; kazıma verisi %3–20 fazla sayıyor).
- Kontrol: Ukrayna Genelkurmayı verisi 7 resmi açıklamayla karşılaştırıldı (Mart–Mayıs 2023), hepsi birebir aynı.
  Rusya Telegram verisi, TASS haberlerinden elle derlenen 21 açıklamayla (data/raw/rusya_mod_iddialari.csv)
  ortak 3 günde karşılaştırıldı: 17 sayının 17'si aynı. Kümülatif sayıda 2 kaynak hatası (23 Mar 2022 uçak,
  27 Oca 2025 topçu) kodda otomatik elendi (model_veri_hazirla.kumulatif_temizle).

## Abartma oranları (iddia ÷ Oryx, medyan)
| İddia eden | tank+zırhlı | topçu | roketatar | uçak | helikopter |
|---|---|---|---|---|---|
| Azerbaycan | 1,2 | 2,0 | 1,2 | 2,0 | – |
| Ermenistan | 7,7 | – | 6,0 | 24,5 | 16,0 |
| Ukrayna | 2,1 | 7,6 | 2,6 | 3,1 | 2,4 |
| Rusya | 5,1 | 19,0 | 17,9 | 6,1 | 7,0 |

Her tarafın abartma oranı savaş boyunca dikkat çekici şekilde sabit (grafik_6): Rusya'nın zırhlı iddiası
2022 ortasından beri Oryx'in 4,4–5,8 katı, Ukrayna'nınki 2022 ortasından sonra 1,7–2,6 katı.

## Model (scripts/model_egit.py)
- Algoritmalar: Random Forest ve Gradient Boosting (log-abartma oranını tahmin eder).
- Özellikler: savaş günü, iddianın aylık artış hızı, kategori (+ Deney 3'te iddia sahibi).
- İddianın büyüklüğü özellik olarak KULLANILMADI: ilk denemede kullanıldığında modeller savaşlar arası çok
  kötüleşti (Rusya-Ukrayna'da sayılar binlerle, Karabağ'da yüzlerle; ağaç modeller bu ölçeği genelleyemiyor).
- Her iddia sahibi eğitimde eşit ağırlıkta (Ukrayna'nın 608 satırı diğerlerini ezmesin).

## Sonuçlar: medyan kat hata (1,00 = mükemmel) — results/model_sonuclari.csv, grafik_7
| Deney | Test | Resmi iddia | Basit düzeltme | Tarafın geçmişi | Random Forest | Gradient Boosting |
|---|---|---|---|---|---|---|
| 1 R-U ile eğit → Karabağ | Azerbaycan | **1,37** | 2,98 | – | 2,21 | 2,24 |
| 1 R-U ile eğit → Karabağ | Ermenistan | 9,17 | **2,94** | – | 3,42 | 3,70 |
| 2 Biri dışarıda | Rusya | 6,17 | 2,66 | – | 2,49 | **2,28** |
| 2 Biri dışarıda | Ukrayna | 2,50 | **2,36** | – | 2,51 | 2,73 |
| 3 Zaman bölmeli (Tem 2023) | Rusya | 6,16 | 2,31 | 1,23 | **1,16** | 1,36 |
| 3 Zaman bölmeli (Tem 2023) | Ukrayna | 2,51 | 1,72 | 1,28 | 1,25 | **1,21** |
| 4a Karabağ zaman bölmeli (sadece Karabağ) | Azerbaycan | 1,46 | 1,34 | 1,35 | 1,15 | **1,13** |
| 4a Karabağ zaman bölmeli (sadece Karabağ) | Ermenistan | 12,22 | 1,44 | 1,38 | 1,76 | **1,21** |
| 4b Karabağ zaman bölmeli (+ R-U verisi) | Azerbaycan | 1,46 | 2,70 | 1,35 | 1,33 | **1,16** |
| 4b Karabağ zaman bölmeli (+ R-U verisi) | Ermenistan | 12,22 | 3,22 | 1,38 | 1,31 | **1,28** |
("Basit düzeltme" = iddiayı eğitimde o kategorinin medyan abartmasına bölmek.)

Deney 4 (Karabağ kendi içinde): 24 Ekim 2020 öncesi 19 iddiayla eğitildi (Azerbaycan 2, Ermenistan 4 açıklama),
sonraki 21 iddia test edildi (Azerbaycan 9, Ermenistan 12) (Azerbaycan 26 Eki ve 1 Ara; Ermenistan 28 Eki, 5 Kas, 8 Kas açıklamaları).
Bu test GERİYE DÖNÜKTÜR: savaş 44 gün sürdüğü için eğitim iddialarının hedefi (60 gün sonraki Oryx) savaş
sırasında henüz bilinemezdi. Test kümesi çok küçük; Gradient Boosting sonuçları satır sırası/rastgelelik
değişince ±0,1 kat oynuyor.

## Yorum
1. **Hiç görmediği bir tarafı düzeltemiyor.** Abartma tarafa özgü: Azerbaycan neredeyse doğru söylemiş
   (1,4 kat), Ermenistan 9 kat abartmış. Diğer taraflardan öğrenilen "ortalama abartma" Azerbaycan'ı bozuyor,
   Ermenistan'ı yetersiz düzeltiyor. Ağaç modeller bu deneylerde basit düzeltmeden de iyi değil.
2. **Tarafın geçmişini görünce çok işe yarıyor.** Temmuz 2023'e kadarki doğrulanmış iddialarla eğitilen
   model, sonraki iki yılın iddialarını düzeltiyor: Ukrayna 2,5 → 1,21 kat (Gradient Boosting),
   Rusya 6,2 → 1,16 kat (Random Forest). Bu, savaş sürerken bir gözlemcinin yapabileceği şeyin ta kendisi.
3. **Karabağ'da da aynı tablo.** Savaşın ilk yarısıyla eğitilen model ikinci yarıdaki iddiaları düzeltiyor:
   Ermenistan 12,2 → 1,21 kat, Azerbaycan 1,5 → 1,13 kat. (Geriye dönük ve küçük test; bkz. yukarı.)
4. **Yapay zeka basit yöntemle başa baş ya da biraz iyi.** Tarafın kendi geçmiş medyanı (B3) zaten güçlü
   (1,23–1,38 kat); Random Forest / Gradient Boosting bunu 1,13–1,21 kata indiriyor. Rusya verisi ilk sürümde
   az olduğunda (38 test satırı) modeller basit yöntemin gerisindeydi; Telegram verisiyle bu tersine döndü.
5. Karabağ'daki "kaybeden çok abartır" bulgusu Rusya-Ukrayna'ya taşınmıyor: orada saldıran taraf (Rusya)
   daha çok abartıyor. "Rol" özelliği eklenen model sürümleri bu yüzden daha kötü çıktı ve çıkarıldı.

## Rusya verisi
İlk sürümde Rusya'nın açıklamaları TASS haberlerinden elle derlendi (21 tarih, 100 satır). Rusya için hazır veri
seti olmadığından (Bakanlık sitesi 2025'ten beri kazınamıyor), 8 Kasım'da Bakanlığın İngilizce Telegram kanalının
herkese açık web sürümü (t.me/s/mod_russia_en) Claude uygulamasının tarayıcısıyla tarandı: Mart 2022 – Haziran 2025
arasında ~haftalık 182 günlük raporun "toplam" satırı okundu. Her satırın kaynak gönderisi: https://t.me/mod_russia_en/<id>.

## Sınırlar
- Sadece 4 iddia sahibi ve 2 savaş var; "hiç görmediği taraf" deneyleri 4 gözlemden ibaret.
- Oryx gerçek kaybın alt sınırı; "abartma" oranları gerçek abartmanın üst sınırıdır.
- Rusya'nın "zırhlı" iddiası piyade hareketlilik araçlarını da kapsıyor olabilir; Oryx tanımında yok.
- Ukrayna "topçu" iddiası havanları da sayıyor olabilir; bu kategori iki tarafta da en yüksek oranları veriyor.
- Rusya-Ukrayna Oryx serisinde 2022-03-19 öncesi kayıtlar o güne yığılmış (kazıma o gün başlamış).

## İleriye dönük kontrol (12 Kasım 2026) — scripts/model_guncel_kontrol.py, grafik_15_guncel_kontrol.png
Modeli güncel veriyle yeniden EĞİTMEK mümkün olmadı: hedef olarak kullanılan günlük Oryx serisi
(scarnecchia/oryx_data) 21 Ağustos 2025'te duruyor (12 Kas 2026'da kontrol edildi, dosya aynı). İddia verileri ise
Kasım 2026'ya kadar var. Bunun yerine Oryx sayfalarının 12 Kasım 2026 kategori başlık toplamları okundu
(data/raw/oryx_ru_ua_anlik_2026-11-12.csv; Rusya toplam 24.275, Ukrayna 12.346; alt toplamlar başlıklarla tutuyor)
ve model, eğitim verisi bittikten ~15 ay sonrası için sınandı.
- Eğitim: model_tablosu.csv'nin tamamı (son iddia 20 Haz 2025). Test: Ukrayna'nın 11 Eyl 2026, Rusya'nın 20 Eki 2026
  iddiaları (Rusya Telegram verisinde Tem 2025 – Eki 2026 arası toplanmadı), 6'şar kategori = 12 tahmin.
- Medyan kat hata: resmi iddia 4,04 → tarafın geçmiş medyanı 1,32 → Gradient Boosting 1,27 → Random Forest 1,13.
  Rusya: 5,30 → 1,24 / RF 1,08. Ukrayna: 2,80 → 1,36 / RF 1,18.
- En kötü tahmin Ukrayna topçu iddiası: iddia Oryx'in 29 katı (eğitim medyanı 7,6); geçmiş medyanla 3,9 kat,
  RF ile 1,5 kat hata. Ukrayna'nın topçu iddiası son dönemde çok hızlandı (21 Ağu 2025'ten beri iddia +20.458,
  Oryx +231). Bütçe modelindeki topçu hedef sayısının geniş aralığı (328–26.548) bu belirsizliği taşıyor.
- Sınır: tek tarihe ait 12 tahmin; Oryx son ayların kayıplarını henüz tam eklememiş olabilir.
