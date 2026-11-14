# Medya ("kalabalık") bulguları – GDELT GKG (6–7 Kasım 2026)

Veri: GDELT GKG 2.0, 27 Eyl – 15 Kas 2020, saatte 1 dosya (~%25 örneklem), İngilizce + çevrilmiş (65 dil) haberler.
2.352 dosya, 15.730 Karabağ makalesi (Rusça 4.234, İngilizce 3.731, Ermenice 1.888, Türkçe 1.620, Azerice 1.015...)
-> 19.607 sayı -> temizlik sonrası 7.700 kayıp sayısı, 1.229 site. Kayıp tarafı belli olan: 1.115 sayı.
Medya grupları: site adına, bulunamazsa dile göre (Ermenice -> Ermeni; Türkçe/Azerice -> Azeri-Türk).
Tablo: results/medya_ozet.csv (script: scripts/medya_sayi_cikar.py)
Kalabalık tahmini = her sitenin o kategoride verdiği en büyük sayının siteler arası medyanı.
Referans: ekipman için Oryx (kanıtlanmış, alt sınır), asker ölüsü için UCDP en iyi tahmin.

## Öne çıkanlar
1. Uluslararası medya toplam kayıp sayısı vermiyor, olay sayısı veriyor.
   Ör. Azeri helikopter kaybı için 84 uluslararası sitenin medyanı = 2 ve bu 84 sitenin 80'i bu sayıyı ilk iki günde (27–28 Eylül) vermiş.
   Azeri tankı: 76 uluslararası site, medyan 3. Kalabalık ilk günün haberine "çakılı" kalmış.
2. Kümülatif (toplam) sayılar neredeyse sadece taraflı medyada var:
   - Ermeni medyası (armenpress, news.am...): Azeri zırhlı 749, İHA 262, tank 181 -> Ermeni resmi iddialarının aktarımı.
   - Azeri-Türk medyası (azernews, aa, yenisafak...): Ermeni tankı 260, topçu 277 -> Azerbaycan MoD aktarımı.
   Yani "kalabalık" bağımsız tahminlerden değil, iki ulusal yankı odasından oluşuyor.
3. Asker ölüleri: medyada Ermeni tarafı için medyan ~300 (150 site; UCDP: 3.900), Azeri tarafı için ~280 (54 site; UCDP: 3.440).
   Savaş sırasında iki taraf da kendi kayıplarını eksik açıkladı; medya bu düşük sayıları taşıdı (UCDP'nin ~%8'i).
4. Sonuç: Bu veriyle klasik "kalabalığın bilgeliği" (bağımsız tahminlerin ortalaması gerçeğe yakınsar) ÇALIŞMIYOR,
   çünkü bağımsızlık ve çeşitlilik varsayımları sağlanmıyor. Bu bir bulgu olarak sunulabilir.

## Sınırlar
- Kayıp tarafı çoğu satırda belirsiz (GKG sayıdan sonra sadece birkaç kelime tutuyor); taraf, sıfattan
  ("Armenian tanks") ya da sitenin hizalamasından (.am -> Ermeni iddiası) çıkarıldı.
- Çevrilmiş haberler çok az ve gürültülü sayı veriyor (makine çevirisi): Ermenice 51, Türkçe 64 sayı.
  Taraflı medya grupları bu yüzden küçük (Ermeni 257, Azeri-Türk 114 tarafı belli sayı).
- resmi_iddialar.csv her günü içermediği için "resmi_ile_ayni" oranı yankının alt sınırıdır.
