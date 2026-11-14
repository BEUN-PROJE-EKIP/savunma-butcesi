-- =====================================================================
-- GDELT GKG 2.0 – 2020 Karabağ savaşı: medyadaki SAYILAR (kalabalık tahminleri)
-- =====================================================================
-- Neden GKG?  GKG her makaleden içindeki sayıları nesneleriyle birlikte çıkarır:
--   Amounts  : "30,Armenian tanks,1532;12,drones,2210;"  (sayı, neyin sayısı, metindeki konum)
--   V2Counts : "KILL#40#soldiers#..."                    (öldürülen/yaralanan vb. sayıları)
-- Yani başlıkta geçmeyen, metnin içindeki kayıp sayıları da yakalanır. DOC API'de bu yok.
--
-- Nasıl çalıştırılır (ücretsiz, kredi kartı gerekmez):
--   1. https://console.cloud.google.com/bigquery adresine Google hesabıyla gir (BigQuery Sandbox).
--   2. Bir proje oluştur, SORGU 1'i yapıştır.
--   3. ÇALIŞTIRMADAN ÖNCE sağ üstte "This query will process X GB" yazısına bak.
--      Ücretsiz kota ayda 1 TB. Beklenen ~100-300 GB. 1 TB'ı geçiyorsa tarih aralığını böl
--      (ör. önce 27 Eyl–20 Eki, sonra 21 Eki–15 Kas).
--   4. Sonuçları "Save results" -> "CSV (local file)" ile indir
--      (10 MB'ı geçerse "CSV (Google Drive)" seç, oradan indir).
--   5. Dosyayı data/raw/gdelt/gkg_sayilar.csv olarak kaydet.
--   6. SORGU 2'yi çalıştır -> data/raw/gdelt/gkg_gunluk.csv
--   7. python scripts/medya_sayi_cikar.py
-- =====================================================================


-- ---------------------------------------------------------------------
-- SORGU 1: Karabağ makalelerindeki ilgili sayılar (her satır = bir sayı)
-- ---------------------------------------------------------------------
WITH makaleler AS (
  SELECT
    DATE                                         AS tarih_saat,   -- YYYYMMDDHHMMSS
    SourceCommonName                             AS domain,
    DocumentIdentifier                           AS url,
    REGEXP_EXTRACT(TranslationInfo, r'srclc:(\w+)') AS kaynak_dil,  -- boşsa İngilizce
    CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64) AS ton,
    Amounts,
    V2Counts
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE _PARTITIONTIME BETWEEN TIMESTAMP('2020-09-27') AND TIMESTAMP('2020-11-15')
    AND (
         REGEXP_CONTAINS(LOWER(V2Locations), r'karabakh|qarabag|artsakh|stepanakert|xankendi|khankendi|shusha|susa')
      OR REGEXP_CONTAINS(LOWER(DocumentIdentifier), r'karabakh|karabag|qarabag|artsakh')
    )
),

miktarlar AS (   -- Amounts alanını sayı-nesne çiftlerine aç
  SELECT
    m.tarih_saat, m.domain, m.url, m.kaynak_dil, m.ton,
    'amount' AS kaynak_alan,
    SAFE_CAST(SPLIT(parca, ',')[SAFE_OFFSET(0)] AS FLOAT64) AS adet,
    LOWER(SPLIT(parca, ',')[SAFE_OFFSET(1)])                AS nesne,
    SAFE_CAST(SPLIT(parca, ',')[SAFE_OFFSET(2)] AS INT64)    AS konum
  FROM makaleler m, UNNEST(SPLIT(m.Amounts, ';')) AS parca
  WHERE parca != ''
),

sayimlar AS (    -- V2Counts: TÜR#SAYI#NESNE#...#KONUM
  SELECT
    m.tarih_saat, m.domain, m.url, m.kaynak_dil, m.ton,
    CONCAT('count_', SPLIT(parca, '#')[SAFE_OFFSET(0)]) AS kaynak_alan,
    SAFE_CAST(SPLIT(parca, '#')[SAFE_OFFSET(1)] AS FLOAT64) AS adet,
    LOWER(SPLIT(parca, '#')[SAFE_OFFSET(2)])                AS nesne,
    SAFE_CAST(SPLIT(parca, '#')[SAFE_OFFSET(ARRAY_LENGTH(SPLIT(parca, '#')) - 1)] AS INT64) AS konum
  FROM makaleler m, UNNEST(SPLIT(m.V2Counts, ';')) AS parca
  WHERE parca != ''
    AND SPLIT(parca, '#')[SAFE_OFFSET(0)] IN ('KILL', 'WOUND', 'SEIZE')
)

SELECT *
FROM (SELECT * FROM miktarlar UNION ALL SELECT * FROM sayimlar)
WHERE adet BETWEEN 1 AND 100000
  AND REGEXP_CONTAINS(nesne,
      r'tank|armou?red|vehicle|artillery|howitzer|mortar|launcher|grad|smerch|drone|uav|bayraktar|harop|helicopter|aircraft|plane|jet|su-25|air defen|s-300|osa|radar|truck|soldier|servicem|troop|militar|fighter|personnel|casualt|dead|killed|wounded|civilian')
ORDER BY tarih_saat;


-- ---------------------------------------------------------------------
-- SORGU 2: Günlük haber hacmi ve ton (küçük sorgu)
-- ---------------------------------------------------------------------
-- SELECT
--   SUBSTR(CAST(DATE AS STRING), 1, 8)                         AS gun,
--   COUNT(*)                                                    AS makale_sayisi,
--   COUNTIF(TranslationInfo IS NULL OR TranslationInfo = '')    AS ingilizce_makale,
--   AVG(CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64))    AS ortalama_ton
-- FROM `gdelt-bq.gdeltv2.gkg_partitioned`
-- WHERE _PARTITIONTIME BETWEEN TIMESTAMP('2020-09-27') AND TIMESTAMP('2020-11-15')
--   AND REGEXP_CONTAINS(LOWER(V2Locations), r'karabakh|qarabag|artsakh|stepanakert|xankendi|khankendi')
-- GROUP BY gun
-- ORDER BY gun;
