"""
Rusya-Ukrayna: farklı silah türlerinin HEDEF KARIŞIMI (taraftan bağımsız sorusu: "bu silah neyi vuruyor?").

Kaynaklar
  1) LostArmour silah etiket sayfaları (data/raw/silah_hedef/lostarmour_diger_silahlar.csv),
     9 Kasım 2026'da Claude uygulamasının tarayıcısıyla sayfa sayfa okundu:
       UMPK güdümlü bomba 3.801/3.802, FPV 1.960 (97.962 kaydın 50 sayfada bir örneklemi), dronla bomba bırakma
       1.598, ÜCSZ helikopter füzeleri 356, LMUR 318, Inokhodets İHA 150, KUB 67.
     Her kayıt videolu bir yayın; hedef türü BAŞLIKTAN anahtar kelimeyle çıkarılır (Rusça).
     Sonuç alanı yok: başlıkta "Уничтожение/уничтожает" geçiyorsa "imha iddiası" sayılır.
  2) LostArmour Lancet tablosu (data/clean/silah_hedef.csv) — hedef türü etikette.
  3) Ukrayna İnsansız Sistemler Kuvvetleri (SBS) ilk yıl özeti (~358 gün, Haz 2025 – Haz 2026; 112.ua / Interfax):
     hedef türüne göre vurulan/imha edilen sayılar. Tarafın kendi iddiası, doğrulanmamış.
Çıktı: data/clean/rus_silah_hedef.csv, results/silah_hedef_karisimi.csv, results/grafik_12_silah_karisimi.png
"""
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
METIN, METIN2, IZGARA, ZEMIN = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "axes.edgecolor": IZGARA,
                     "xtick.color": METIN2, "ytick.color": METIN2, "axes.facecolor": ZEMIN,
                     "figure.facecolor": ZEMIN, "savefig.facecolor": ZEMIN})

# sıra önemli: ilk eşleşen kazanır
KURAL = [
    ("Saldırı değil", r"Доставка|доставк|корректируют|Последствия|разведк|обзор"),
    ("İKA / kara robotu", r"НРТК|НРК|робот"),
    ("Hava savunma", r"ЗРК|ПВО|IRIS|Patriot|NASAMS|Бук|«Оса»|\bОса\b|С-300|Gepard|ПЗРК|ЗСУ-23|ЗУ-23|Stinger|Avenger|Skynex|Hawk|Crotale"),
    ("Radar / EH", r"старлинк|РЛС|радар|РЭБ|РЭР|антенн|Starlink|ретранслятор|связи|AN/TPQ|пеленгатор|радиовышк|вышк"),
    ("Dron ekibi / fırlatma noktası", r"ПУ Бп?ЛА|пункт[а-я]* управления Бп?ЛА|оператор[а-я]* Бп?ЛА|расч[её]т[а-я]* Бп?ЛА|пилот|точк[а-я]* взл[её]та|мастерск[а-я]* Бп?ЛА|Бп?ЛА-?шник|наземн[а-я]* станци"),
    ("Tank", r"танк|Leopard|Abrams|Challenger|Т-64|Т-72|Т-80|PT-91"),
    ("Roketatar", r"РСЗО|HIMARS|M142|M270|\bГрад\b|Ураган|Смерч|RM-70|БМ-21"),
    ("Topçu", r"гаубиц|САУ|оруди|артиллер|M777|M109|миномет|миномёт|Богдана|Краб|CAESAR|PzH|Archer|Zuzana|Dana|Гвоздик|Акаци|Мста|Гиацинт|Пион|Д-30|Д-20|FH-70|L119|AS-90"),
    ("Zırhlı araç", r"БМП|БТР|бронетехник|ББМ|M113|MaxxPro|Bradley|бронеавтомобил|Козак|Kozak|Stryker|Marder|CV90|MRAP|\bЛБ\b|Humvee|HMMWV|Хамви|бронемашин|Spartan|Husky|Senator|Новатор|БРДМ|МТ-ЛБ|ИМР|БРЭМ"),
    ("Deniz aracı", r"БЭК|МБЭК|катер|лодк|плавсредств|USV|безэкипажн|судн"),
    ("Lojistik araç", r"автотранспорт|грузовик|пикап|автомобил|транспорт|автобус|машин|КрАЗ|тягач|квадроцикл|мотоцикл|багги|цистерн"),
    ("Araç (türü belirsiz)", r"техник|\bавто"),
    ("Piyade", r"пехот|личн[а-я]* состав|живой сил|живая сила|военнослужащ|солдат|ДРГ|штурмов[а-я]* групп|бойц|боевик|ротационн|групп[а-я]* ВСУ|групп[а-я]* боевик"),
    ("Mevzi / bina / altyapı", r"ПВД|временной дислокации|склад|\bБК\b|боеприпас|здани|дом|казарм|ангар|цех|завод|объект|предприяти|школ|гараж|укрыти|блиндаж|опорн|позици|окоп|штаб|\bКП\b|командн|подстанци|энерге|мост|переправ|ДОТ|строени|дислокаци|башн|сооружени|промзон|зернохранилищ|расположени|лесопосадк|скоплени|пункт|\bОП\b|\bПУ\b|АЗС|\bПС\b|оборудовани|насып|минн|имуществ|инфраструкт|ТЭЦ|котельн|железнодорож|вокзал|порт"),
    ("İHA", r"Перехват|сбит|по FPV|FPV-дрон|дрону|по Бп?ЛА|Бп?ЛА «|Бп?ЛА \"|Баб[аы][- ]Яг|Вампир|воздушн[а-я]* цел|Бп?ЛА|Лют|Бобер|Анубис|Чаклун|Майя|R18|Шарк|Fly ?Eye|Лелека|Hornet|квадрокоптер|коптер|мавик|Mavic"),  # en sonda: BPLA kelimesi silah adı olarak da geçer
]
KURAL = [(k, re.compile(p, re.I)) for k, p in KURAL]
IMHA = re.compile(r"Уничтожени|уничтожа|уничтожил|уничтожен|Ликвидаци|ликвидир", re.I)
ETIKET = {"umpk": "Güdümlü bomba (UMPK)", "fpv": "FPV dron", "sbros": "Dronla bomba bırakma",
          "helicopters": "Helikopter füzesi", "lmur": "LMUR füzesi", "inokhodets": "Inokhodets İHA",
          "kub": "KUB dolanan mühimmat"}
LANCET_GRUP = {"topcu": "Topçu", "tank": "Tank", "zirhli_arac": "Zırhlı araç", "lojistik_arac": "Lojistik araç",
               "radar_eh": "Radar / EH", "hava_savunma": "Hava savunma", "roketatar": "Roketatar",
               "deniz_araci": "Deniz aracı", "mevzi_bina": "Mevzi / bina / altyapı", "piyade": "Piyade", "iha": "İHA",
               "hava_araci": "Diğer", "yem": "Diğer", "diger": "Diğer", "belirsiz": "Belirsiz"}
# SBS ilk yıl özeti (Ukrayna dronları -> Rus hedefleri); kaynak: 112.ua / Interfax-Ukraine
SBS = {"Hava savunma": 248, "Tank": 817, "Zırhlı araç": 1379, "Topçu": 4890 + 342, "Roketatar": 281,
       "Lojistik araç": 26430, "İHA": 29903 + 7633, "Diğer": 13, "Dron ekibi / fırlatma noktası": 10848}
GRUPLAR = ["İKA / kara robotu", "Tank", "Zırhlı araç", "Topçu", "Roketatar", "Hava savunma", "Radar / EH", "Lojistik araç",
           "Deniz aracı", "Araç (türü belirsiz)", "Dron ekibi / fırlatma noktası", "İHA", "Piyade", "Mevzi / bina / altyapı", "Diğer"]


def sinif(t):
    for k, r in KURAL:
        if r.search(str(t)):
            return k
    return "Diğer"


def main():
    d = pd.read_csv(KOK / "data/raw/silah_hedef/lostarmour_diger_silahlar.csv", encoding="utf-8-sig")
    d["silah"] = d.silah_etiketi.map(ETIKET)
    d["hedef_grup"] = d.baslik.map(sinif)
    d = d[d.hedef_grup != "Saldırı değil"].copy()  # ikmal, keşif, düzeltme videoları
    d["imha_iddiasi"] = d.baslik.str.contains(IMHA).astype(int)
    d.to_csv(KOK / "data/clean/rus_silah_hedef.csv", index=False)
    print("Sınıflanamayan (Diğer) payı:", d.groupby("silah").hedef_grup.apply(lambda s: round((s == "Diğer").mean(), 3)).to_dict())

    sh = pd.read_csv(KOK / "data/clean/silah_hedef.csv")
    la = sh[sh.kaynak == "LostArmour"].copy()
    la["hedef_grup"] = la.hedef.map(LANCET_GRUP).fillna("Diğer")
    la = la[la.hedef_grup != "Belirsiz"]

    say = d.groupby(["silah", "hedef_grup"]).size().unstack(fill_value=0)
    say.loc["Lancet dolanan mühimmat"] = la.hedef_grup.value_counts()
    say.loc["Ukrayna dronları (SBS, iddia)"] = pd.Series(SBS)
    say = say.fillna(0).reindex(columns=GRUPLAR, fill_value=0)
    kayit = say.sum(1)
    pay = 100 * say.div(kayit, axis=0)
    ozet = pay.round(1).add_prefix("pay_%_")
    ozet.insert(0, "kayit", kayit.astype(int))
    imha = d.groupby("silah").imha_iddiasi.mean().mul(100).round(0)
    ozet.insert(1, "basliklarda_imha_iddiasi_%", imha.reindex(ozet.index))
    ozet.to_csv(KOK / "results/silah_hedef_karisimi.csv")
    print(ozet.to_string())
    grafik(pay, kayit)


def grafik(pay, kayit):
    sira = ["Lancet dolanan mühimmat", "KUB dolanan mühimmat", "Inokhodets İHA", "LMUR füzesi", "Helikopter füzesi",
            "Güdümlü bomba (UMPK)", "FPV dron", "Dronla bomba bırakma", "Ukrayna dronları (SBS, iddia)"]
    sira = [s for s in sira if s in pay.index]
    P = pay.loc[sira]
    sutun = [g for g in GRUPLAR if P[g].max() >= 1]
    M = P[sutun].values
    fig, ax = plt.subplots(figsize=(16, 8.2))
    fig.subplots_adjust(top=0.84, bottom=0.25, left=0.25, right=0.99)
    fig.text(0.02, 0.94, "Rusya-Ukrayna: her silah türü neyi vuruyor?", fontsize=18, color=METIN, fontweight="bold")
    fig.text(0.02, 0.885, "Satır = silah türü; hücre = o silahın belgelenmiş saldırılarının hedef türüne dağılımı (%). "
             "Parantez içi: kayıt sayısı.", fontsize=12, color=METIN2)
    ax.imshow(M, aspect="auto", cmap="Blues", vmin=0, vmax=70)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if M[i, j] >= 0.5:
                ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=10.5,
                        color="white" if M[i, j] > 40 else METIN)
    ax.set_xticks(range(len(sutun)), sutun, rotation=35, ha="right", fontsize=10.5)
    ax.set_yticks(range(len(sira)), [f"{s} ({int(kayit[s]):,})".replace(",", ".").replace("SBS. ", "SBS, ") for s in sira], fontsize=11)
    ax.axhline(len(sira) - 1.5, color=METIN, linewidth=1.5)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xticks(np.arange(-0.5, len(sutun)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(sira)), minor=True)
    ax.grid(which="minor", color=ZEMIN, linewidth=2)
    ax.tick_params(which="minor", length=0)
    fig.text(0.02, 0.03, "Rus silahları: LostArmour (videolu yayınlar; hedef türü başlıktan, FPV 97.962 kaydın örneklemi). "
             "Son satır: Ukrayna İnsansız Sistemler Kuvvetleri ilk yıl özeti\n(Rus hedefleri; tarafın kendi iddiası, "
             "piyade sayılmadı). Hedef karışımıdır, atış başına verim değildir.", fontsize=9.5, color=METIN2)
    fig.savefig(KOK / "results/grafik_12_silah_karisimi.png", dpi=150)


if __name__ == "__main__":
    main()
