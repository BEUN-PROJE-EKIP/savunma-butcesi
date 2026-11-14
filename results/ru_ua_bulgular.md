# Rusya-Ukrayna: resmi iddialar vs Oryx (8 Kasım 2026)

Script: scripts/ru_ua_karsilastirma.py -> results/ru_ua_ozet.csv, results/grafik_8_ru_ua_kategoriler.png
Oran = iddia ÷ Oryx'in fotoğrafla kanıtladığı kayıp (iddiadan 60 gün sonraki sayım). Oryx alt sınır olduğundan
oran, abartmanın üst sınırıdır. Dönem: Mart 2022 – Haziran 2025, iki taraf da haftalık.

## Son durum (20 Haziran 2025 iddiaları)
| Kategori | Ukrayna'nın iddiası (Rus kaybı) | Oryx | Oran | Rusya'nın iddiası (Ukrayna kaybı) | Oryx | Oran |
|---|---|---|---|---|---|---|
| Tank + zırhlı | 33.814 | 13.146 | 2,6× | 23.982 | 4.884 | 4,9× |
| Topçu | 29.374 | 1.456 | 20,2× | 26.413 | 862 | 30,6× |
| Roketatar | 1.421 | 514 | 2,8× | 1.572 | 88 | 17,9× |
| Hava savunma | 1.188 | 467 | 2,5× | 611 | 227 | 2,7× |
| Uçak | 416 | 164 | 2,5× | 663 | 110 | 6,0× |
| Helikopter | 337 | 159 | 2,1× | 283 | 52 | 5,4× |

## Yıllara göre medyan oran
| Kategori | Ukrayna 2022 → 2025 | Rusya 2022 → 2025 |
|---|---|---|
| Tank + zırhlı | 1,9 → 2,5 | 5,0 → 4,9 |
| Topçu | 3,2 → 18,0 | 22,3 → 28,9 |
| Roketatar | 2,1 → 2,7 | 22,9 → 17,8 |
| Hava savunma | 1,0 → 2,5 | 5,2 → 2,7 |
| Uçak | 3,9 → 2,6 | 5,5 → 6,1 |
| Helikopter | 2,7 → 2,1 | 11,9 → 5,5 |

## Bulgular
1. **İki taraf da abartıyor; Rusya çoğu kategoride daha fazla.** Ukrayna'nın iddiaları Oryx'in genelde 2–3 katı,
   Rusya'nınkiler 5–6 katı (zırhlı, uçak, helikopter). Roketatarda fark en büyük: Rusya 17,9×, Ukrayna 2,8×.
2. **Hava savunmada iki taraf eşit (~2,5–2,7×).** Rusya'nın oranı 2022'de 5× iken düştü, Ukrayna'nınki 1×'ten yükseldi.
3. **Topçu iki tarafta da aşırı (20–30×) ve Ukrayna'da sürekli artıyor (3× → 20×).** Muhtemel neden tanım farkı:
   iki taraf da havanları sayıyor ("field artillery guns and mortars" / "artillery systems"), Oryx'in topçu sayımı
   (kundağı motorlu + çekili topçu) havanları büyük ölçüde içermiyor. 2024'ten sonra drone savaşıyla birlikte
   tarafların saydığı "topçu" kalemleri hızla artarken Oryx'teki büyük topçu kayıpları yavaşladı. Bu kategori
   "abartma" olarak değil, "tanım uyuşmazlığı" olarak yorumlanmalı.
4. **Oranlar zamanla dikkat çekici şekilde sabit.** Rusya'nın zırhlı oranı 2022 ortasından beri 4,4–5,8×;
   Ukrayna'nınki 2023'ten beri 2,0–2,6× arasında yavaşça artıyor. Her tarafın kendi "tarzı" var; yapay zeka
   modelinin tarafın geçmişinden öğrenebilmesinin nedeni bu (results/model_bulgular.md, Deney 3).
5. **İlk haftalarda iddialar Oryx'in gerisinde (oran < 1).** Savaşın başında Oryx'in kayıtları yığılarak eklendi
   (kazıma 19 Mart 2022'de başladı) ve tarafların sayımı henüz hızlanmamıştı; ilk 1–2 ay yorumlanmamalı.

## Dikkat
- Oryx kanıtlanmış kaybın alt sınırı. Gerçek kayıp Oryx'ten yüksek; yani gerçek abartma buradaki oranlardan küçük.
- Ukrayna'nın kayıpları Rus kayıplarından daha az görüntüleniyor olabilir (savaş Ukrayna topraklarında, Ukrayna
  kendi kayıplarının görüntülerini kısıtlıyor). Bu, Rusya'nın oranını yapay olarak büyütebilir.
- Rusya'nın "zırhlı" sayısı hafif zırhlı araçları da içeriyor olabilir; Oryx'in zırhlı muharebe aracı tanımında yok.
