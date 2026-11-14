# Silah → hedef → sonuç ve bütçe dağılımı — bulgular (9 Kasım 2026)

## Veri
- LostArmour Lancet tablosu: 5.197 videolu saldırı (Tem 2022 – 3 Kas 2026); sonucu belli olan 3.434 saldırı modelde.
- Oryx Karabağ 2020: vuran silahı belli 669 kayıp (TB2 548, dolanan mühimmat 72, Spike 49) — ıska yok,
  bu yüzden imha olasılığına değil hedef karışımına katkı verir.
- Birim fiyatlar: data/raw/silah_hedef/birim_maliyetler.csv (kaynaklı aralıklar; bazıları VARSAYIM olarak işaretli).

## 1. İmha olasılığı modeli (scripts/imha_modeli.py)
- 2025 sonrası "sonuç bilinmiyor" oranı %42-63'e çıkıyor; hedef bazında imha oranı yıllara göre değişiyor
  (tank: 2023 %12 → 2026 %44). Bu yüzden geçmişle eğitip geleceği tahmin etmek (zaman bölmeli test) zor.
- 5 katlı çapraz doğrulamada imha için Brier skoru: genel oran 0,219 → hedef türü tablosu 0,204 →
  Random Forest 0,201. Yani sonucu belirleyen asıl şey HEDEF TÜRÜ; model tabloya küçük bir katkı ekliyor.
- Güncel (2024-2026) imha olasılıkları: radar %57, lojistik araç %54, hava savunma füze %41,
  kundağı motorlu top %35, tank %31, hafif zırhlı %31, çekili top %22. Iska %4-9.

## 2. Maliyet etkinliği (scripts/butce_optimizasyonu.py)
Harcanan 1 $ karşılığı beklenen kayıp (medyan; %10-%90):
- Hava savunma (füze) ~208× (108-456), radar ~95× (37-242), kundağı motorlu top ~40× (25-68)
- tank ~17×, çekili top ~13×, hafif zırhlı ~12×
- lojistik araç ~1,4× (0,8-2,6), maket ~0,1×  → Lancet'i kamyona harcamak neredeyse başa baş; yeme harcamak zarar.

## 3. Bütçe dağıtımı (doğrusal programlama)
- 2024-2026'da 3.916 Lancet saldırısının %16'sı lojistik araca, %15'i hafif zırhlıya gitmiş.
- Aynı sayıda Lancet, her hedef türünden en çok 1,5 kat bulunabileceği varsayımıyla yeniden dağıtılırsa
  beklenen kayıp ~1,36 kat (2 kat varsayımıyla ~1,64 kat) artıyor. Optimal dağılım ucuz hedefleri bırakıp
  hava savunma, radar ve topçuya yükleniyor.

## Sınırlamalar
- Sadece yayınlanan videolar: başarılar fazla temsil edilir (bir birliğin 100 Lancet'le 3 isabet aldığı da
  bildirildi). Mutlak oranlar üst sınırdır; SIRALAMA ve dağılım karşılaştırması daha güvenilir.
- Fiyatlar yaklaşık; Monte Carlo ile aralık verildi. Kamyon vurmanın lojistiği kesme gibi parasal olmayan
  değeri modelde yok.
- Saldırı bazında sonuç verisi yalnızca Lancet için var; FPV, topçu vb. ile silahlar arası bütçe
  karşılaştırması için benzer veri gerekir.

## 4. Üç savaş karşılaştırması (scripts/uc_savas_karsilastirma.py, grafik_11_uc_savas.png)
Silah türü -> hedef türü -> belgelenmiş kaybın değeri (atış başına verim DEĞİL; atılan mühimmat sayısı
yalnızca Lancet'te biliniyor):
- Karabağ 2020: TB2 548 kayıp ~672 mn $ (hava savunma %39, topçu %22, tank %19); dolanan mühimmat 72 kayıp
  ~225 mn $ (%81 hava savunma); Spike 49 kayıp ~53 mn $ (%70 tank).
- Rusya-Ukrayna: Lancet ~3,1 mrd $ (topçu %37, radar/EH %24, hava savunma %18) — "bilinmiyor" sonuçlar sayılmadı.
- İran-ABD 2026 (CRS IN12692, 81 uçak; dost ateşi/kaza/kendi imhası hariç): balistik füzelerle üslerde
  yerdeki 15 uçak ~800 mn $ (E-3 tek başına 500 mn $); hava savunma/yer ateşiyle 7 hava aracı ~358 mn $;
  nedeni belirtilmemiş 45 MQ-9 ~1,35 mrd $.
- Ortak ders: ucuz, isabetli silahlar en çok değeri HAVA SAVUNMA, RADAR ve TOPÇU gibi pahalı ama sabit/yavaş
  hedeflerde buluyor; ABD tarafında en pahalı kayıplar havada değil YERDE (üslerde) yaşandı. Ürdün saldırısında
  ~20 balistik füzeye karşı 30'dan fazla Patriot (~4 mn $/adet) atıldı -> savunma tarafında bütçe sorusu
  "önleyici füze mi, sığınak/dağıtma mı?" olarak karşımıza çıkıyor.

## 5. Rusya-Ukrayna: her silah türü neyi vuruyor? (scripts/rus_silahlari_hedef.py, grafik_12_silah_karisimi.png)
LostArmour'un silah sayfalarından 8.250 videolu yayın (UMPK 3.801, FPV 1.960 örneklem / 97.962, dronla bomba
bırakma 1.598, helikopter füzesi 356, LMUR 318, Inokhodets 150, KUB 67; hedef türü başlıktan) + Lancet tablosu +
Ukrayna İnsansız Sistemler Kuvvetleri ilk yıl özeti (Rus hedefleri, iddia; piyade hariç). Hedef karışımı, verim değil.
- Güdümlü bomba (UMPK) %86 ve LMUR %72 mevzi/bina/altyapı; LMUR'un %18'i dron fırlatma noktası.
- Lancet %43 topçu, %17 lojistik, %14 zırhlı, %12 tank — ağır teçhizat avcısı.
- Helikopter füzeleri %25 zırhlı + %9 tank (+%17 türü belirsiz araç).
- FPV %40 karşı-dron (İHA önleme), %15 anten/Starlink, %19 mevzi; dronla bomba bırakma %41 piyade.
- Ukrayna dronları (SBS): %45 İHA (keşif + Şahed), %32 lojistik araç, %13 dron fırlatma noktası, %6 topçu.
- Ders: tek bir "en iyi silah" yok; her silah türü belli bir hedef sınıfına uzmanlaşmış. Bütçe, düşmanın
  hangi hedef sınıfına yaslandığına göre silah KARIŞIMI olarak planlanmalı. Dron savaşında hedeflerin önemli
  kısmı artık karşı tarafın dronları ve dron ekipleri.

## 6. Senaryo: 30 milyar $'lık bir yıllık savunma bütçesi (scripts/butce_30_milyar.py, grafik_13_butce_30mlr.png)
Rusya-Ukrayna benzeri kara savaşı yürüten bir taraf; 8 seçenek (FPV, Lancet tipi, 155 mm mermi, güdümlü bomba,
GMLRS, tanksavar, önleyici dron, Patriot). Amaç: düşmana verilen ekipman kaybı + önlenen hasar ($) en büyük.
Doğrusal programlama; bütçe, yıllık üretim kapasitesi ve bulunabilecek hedef/gelen tehdit sayısı kısıt.
2.000 Monte Carlo çekilişi + tek tek değiştirmeli duyarlılık (tornado).

Girdiler (scripts/butce_girdileri_veriden.py ile üretildi):
- Hedef sayıları VERİDEN: Ukrayna Genelkurmayı'nın son 12 ayı (2025-11-07 → 2026-11-07) iddiası, bu projenin
  2024-25 abartma oranlarına (iddia/Oryx) bölünerek alt sınır; iddia x 1,5 üst sınır; orta = geometrik ortalama.
  Örnek: tank iddia 1.126 → 352 / 629 / 1.689; topçu iddia 17.699 (oran 54) → 328 / 2.410 / 26.548;
  araç-yakıt tankeri iddia 104.666 → 32.708 / 58.510 / 156.999. Dron ekibi, mevzi, İHA hâlâ varsayım.
- Üretim kapasitelerinin 6/8'i kaynaklı (FPV, 155 mm, Patriot ~620/yıl, GMLRS ~14.000/yıl, Javelin ~3.960/yıl,
  önleyici dron ~550.000/yıl). Lancet tipi ve güdümlü bomba kapasitesi ile fiyatı VARSAYIM.
- Etkinlik değerleri VARSAYIM, toplam saha rakamlarına göre kalibre (etkinlik_notlari.md).

Bulgular:
- 8 silahın bir yılda üretilebilen TAMAMINI almak 19,8 mrd $ tutuyor. Yani 30 mrd $ bu mühimmatlara
  bir yılda fiziksel olarak harcanamaz; sorun "hedef bitmesi" değil, öncelikle ÜRETİM KAPASİTESİ.
- Orta senaryo (A): 13,0 mrd $ anlamlı harcanıyor: 155 mm 3,3, Patriot 3,1, GMLRS 2,7, FPV 2,4,
  güdümlü bomba 0,9, önleyici dron 0,7; Lancet ve tanksavar seçilmiyor. Kalan ~17 mrd $ ek getiri üretmiyor.
- Hedef alt sınır (B, Oryx düzeyi): 6,5 mrd $. Hedef üst sınır (C): 19,8 mrd $ (tüm kapasite dolu).
  C + kapasite 3 kat (D): 25,3 mrd $; en büyük kalem Patriot 9,3 mrd $.
- Monte Carlo: kullanılan bütçe medyan 16,6 mrd $ (%10-%90: 10,8-20,9); hiçbir çekilişte 30 mrd dolmadı.
- Duyarlılık (orta 13,0): fiyatlar düşük/yüksek 8,4/22,1; etkinlik x0,5/x2 19,8/6,3; hedef sayısı alt/üst
  6,5/19,8; FPV kapasitesi 18,0/10,7; güdümlü bomba 15,0/9,9; Patriot 11,5/15,5; GMLRS 14,5/11,3.
  Lancet, tanksavar, mermi, önleyici dron kapasitesi ve hedef değerleri sonucu değiştirmiyor; yani
  kaynak bulunamayan iki kapasite (Lancet, güdümlü bomba) ana sonucu taşımıyor.
- Ders: "kaç para" sorusundan önce "kaç tane üretilebiliyor" ve "kaç hedef bulunabiliyor" soruları geliyor;
  fazla bütçenin en iyi kullanımı üretim kapasitesine yatırım. Kapasiteler üreticilerin TOPLAM üretimi
  (tek alıcının hepsini alması iyimser). İnsan kaybı parayla ölçülmedi. Karar-destek senaryosudur,
  gerçek bütçe önerisi değildir.

## 7. Kısıtlı bütçe: 6 ve 10 milyar $ (scripts/butce_10_milyar.py, grafik_14_butce_10mlr.png)
Aynı model ve girdiler; bütçe 30 yerine 6 ve 10 mrd $. Ek olarak "verimlilik eşiği": son 1 $'ın düşmana
1 $'dan az ekipman kaybı verdirmeye başladığı bütçe (LP'nin bütçe gölge fiyatı < 1).
- Verimlilik eşiği (orta parametreler): A orta 6,2 mrd $ · B az hedef 5,3 · C bol hedef 8,5 · D bol hedef +
  3 kat üretim 17,7. Monte Carlo (2.000): medyan 7,7 mrd $ (%10-%90: 5,9-11,2); çekilişlerin %82'sinde 10'un altında.
- Orta senaryoda eşiğe kadar getiri 58,2 mrd $; 10 mrd $'da 60,3; doyunca (13 mrd $) 61,0. Yani son ~4 mrd $
  ekipman değeri olarak yalnızca ~2 mrd $ ek kayıp verdiriyor (son dolar getirisi 0,25-0,67 $).
- 6 mrd $ (orta): Patriot 3,1, FPV 1,5, önleyici dron 0,7, güdümlü bomba 0,7 → getiri 58 mrd $ (9,7 kat).
- 10 mrd $ (orta): Patriot 3,1, GMLRS 2,7, FPV 2,4, güdümlü bomba 0,9, önleyici dron 0,7, 155 mm 0,2 → 60 mrd $ (6,0 kat).
- Her senaryoda ve bütçede ilk kalem Patriot (~3,1 mrd $, kapasite dolu) ve önleyici dron: gelen tehdidi
  durdurmak en yüksek getirili kullanım. Hedef bolsa (C) 10 mrd $'da Lancet ve tanksavar da devreye giriyor;
  üretim 3 katsa (D) 10 mrd $'ın 7,3'ü Patriot.
- Az hedefte (B) 10 mrd $'ın 3,5'i harcanamıyor: vurulacak hedef yok.
- Monte Carlo 10 mrd $: çekilişlerin %94'ünde para tamamen harcanıyor (bütçe gerçek kısıt). Patriot, FPV,
  önleyici dron her çekilişte seçiliyor; güdümlü bomba %98, GMLRS %85; Lancet %47, mermi %41, tanksavar %8.
- Yorum: ~6 mrd $ ekonomik verimlilik sınırı (ekipman değeriyle ölçülen getiri), 10 mrd $ askerî ihtiyaç
  bütçesi. Eşikten sonraki harcamanın gerekçesi modelde parasal karşılığı olmayan etkiler (piyade bastırma,
  can kaybı önleme). Model, kararın hangi noktadan sonra para değil politika meselesi olduğunu gösteriyor.
