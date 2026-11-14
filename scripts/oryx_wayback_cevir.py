"""
Wayback Machine'deki Oryx kopyalarından çıkarılan kümülatif kayıp sayılarını CSV'ye çevirir.
Girdi : data/raw/oryx_wayback_kodlu.txt  (tarih|taraf|kategori=sayı,...)
Çıktı : data/clean/oryx_zaman_serisi.csv (uzun format) ve oryx_zaman_serisi_genis.csv
Notlar:
- Kategoriler Oryx başlıklarındaki toplamlardır (ele geçirilenler dahil).
- X_ ile başlayanlar (stratejik hedef, ATGM, MANPADS) araç değildir; sonraki sürümlerde listeden çıkarılmıştır.
- K_ ile başlayanlar kayıt-link sayımlarıdır (K_dolanan: dolanan mühimmatla vurulduğu yazan, K_spike: Spike ATGM).
- 'TB2 ile vuruldu' etiketi Ocak 2021 sonuna kadarki hiçbir kopyada yok; sonradan eklenmiş.
- Oryx 13-16 Ocak 2021 kopyalarında Ermeni tank sayısını '2287' yazmış (yazım hatası); bu tarihler dosyaya alınmadı.
"""
import pandas as pd

rows = []
for line in open("data/raw/oryx_wayback_kodlu.txt", encoding="utf-8"):
    tarih, taraf, kv = line.strip().split("|")
    for p in kv.split(","):
        k, v = p.split("=")
        rows.append({"tarih": pd.to_datetime(tarih), "kayip_taraf": "Ermenistan" if taraf == "E" else "Azerbaycan",
                     "kategori": k, "kumulatif": int(v)})
df = pd.DataFrame(rows)
df["savas_gunu"] = (df.tarih - pd.Timestamp("2020-09-27")).dt.days + 1
df.to_csv("data/clean/oryx_zaman_serisi.csv", index=False, encoding="utf-8-sig")
arac = df[~df.kategori.str.startswith(("X_", "K_"))]
genis = arac.pivot_table(index=["tarih", "savas_gunu"], columns=["kayip_taraf", "kategori"], values="kumulatif", fill_value=0)
genis.to_csv("data/clean/oryx_zaman_serisi_genis.csv", encoding="utf-8-sig")
top = arac.groupby(["tarih", "kayip_taraf"]).kumulatif.sum().unstack()
print(top.to_string())
