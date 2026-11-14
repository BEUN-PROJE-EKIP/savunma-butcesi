# Etkinlik matrisi notları (etkinlik_matrisi.csv)

Her hücre: o silahın, o hedef türüne yöneltilen BİR atışının hedefi etkisiz hale getirme olasılığı
(hedefi bulamama, karıştırma/EH, ıska, tekrar atış, hasarın tamir edilmesi dahil "sahada" ortalama).

Kalibrasyon yaklaşımı — yayınlanan videolardaki oranlar sahadaki ortalamadan çok yüksek olduğu için toplam
rakamlara göre düşürüldü:
- FPV: Ukrayna 2025'te ~4 milyon dron üretti; Drone Ordusu Bonus 2025'te 62 bin hafif + 29 bin ağır araç vuruşu
  bildirdi (iddia). Araçlara yöneltilen dron başına ~%2-5 etkisiz hale getirme -> lojistik 0,04, tank 0,008.
  Tek operatör verisi (War on the Rocks): isabet %20-43; isabet sonrası araç yok etme olasılığı düşük.
- Lancet: bu projenin imha modelindeki (yayınlanan video) değerler x 0,35. Gerekçe: yayınlanmayan ıskalar ve
  düşürülenler; bir birliğin 100 Lancet ile 3 isabet aldığı bildirildi. Belirsizlik çarpanı 0,4-2,0
  (yani 0,07 ile yayın değerleri arası).
- 155 mm mermi: mermi başına çok düşük (bastırma ateşi, hedef bulma); 57. Tugay'ın "1-3 mermi" ifadesi
  iyi koşulların üst sınırı. Belirsizlik çarpanı 0,3-3.
- Güdümlü bomba: sabit hedeflerde (mevzi/bina) yüksek, araçta çok düşük; GPS karıştırma ile isabet düşüyor.
- GMLRS, tanksavar: hassas, ama hedefe erişim (menzil, görüş) sınırlı.
- Önleyici dron: hedef başına 2-3 önleyici gerekiyor (Zelenski: %68; üretici: %80-92) -> önleyici başına ~0,35.
- Patriot: VARSAYIM ~0,9.
Hepsi tartışmaya açık VARSAYIMDIR; Monte Carlo bu belirsizliği taşır.
