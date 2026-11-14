# Arşiv: projenin ilk aşaması (Karabağ 2020, "kalabalığın bilgeliği")

Bu klasördekiler projenin son zincirinde (abartma → silah-hedef → bütçe) kullanılmıyor; silinmedi, buraya taşındı
(12 Kasım 2026).

- `scripts/` : GDELT medya verisini çeken ve işleyen betikler (`gdelt_*`, `medya_sayi_cikar.py`), Karabağ grafikleri
  (`grafikler.py`), ilk iddia/Oryx tablosu (`iddia_vs_oryx.py`).
- `data/raw/gdelt/` : GDELT GKG'den 15.730 Karabağ haberi ve içlerindeki sayılar.
- `data/clean/medya_iddialari.csv`, `ucdp_karabag.csv`, `data/raw/ucdp_ged261_karabag.tsv` : medya iddiaları ve UCDP ölüm verisi.
- `results/` : grafik 1–5, `ilk_bulgular.md`, `medya_bulgular.md`, `medya_ozet.csv`, `iddia_vs_oryx.csv`.
- `README_eski.md` : projenin o dönemdeki README'si (bütün ayrıntılar orada).

Ana bulgu: medya "kalabalığı" bağımsız değil; toplam kayıp sayılarını yalnızca taraflı medya veriyor ve kendi
hükümetinin iddiasını tekrarlıyor. Bu yüzden klasik kalabalığın bilgeliği burada çalışmıyor.

Betikleri yeniden çalıştırmak için ana klasördeki yerlerine geri taşımak gerekir (yollar ana klasöre göre yazıldı;
`resmi_iddialar.csv` ve Oryx Karabağ tabloları ana klasörde kaldı).
