"""
Medyadaki kayıp sayılarını ("kalabalığın tahminleri") çıkarır ve Oryx + resmi iddialarla karşılaştırır.

Girdiler (hangisi varsa kullanılır):
    data/raw/gdelt/doc_makaleler.csv  (scripts/gdelt_doc_cek.py)      -> BAŞLIKLARDAN sayı çıkarılır
    data/raw/gdelt/gkg_sayilar.csv    (scripts/gdelt_gkg_bigquery.sql) -> GKG'nin metinden çıkardığı sayılar
    data/raw/resmi_iddialar.csv, data/clean/oryx_karabag_ozet.csv     -> karşılaştırma için

Çıktılar:
    data/clean/medya_iddialari.csv : her satır = bir kaynakta geçen bir sayı
        tarih, kaynak_turu (baslik/gkg), domain, url, dil, adet, proje_kategori,
        kayip_taraf, iddia_eden, resmi_ile_ayni, metin
    results/medya_ozet.csv         : kategori bazında kalabalık tahmini vs resmi iddia vs Oryx

Kalabalık tahmini nasıl hesaplanıyor:
    1. Her haber sitesi (domain) için, o kategoride savaş boyunca verdiği EN BÜYÜK sayı alınır
       (iddialar kümülatif olduğu için en büyük = o sitenin "son" tahmini).
    2. Siteler arası MEDYAN = kalabalığın tahmini (ortalama aykırı değerlere çok duyarlı).
       Ayrıca geometrik ortalama da verilir (Galton'un öküz deneyindeki gibi log-ölçekte ortalama).

Önemli uyarı (sunumda söylenmeli):
    Kalabalığın bilgeliği, tahminlerin BAĞIMSIZ olmasını ister. Haber siteleri çoğu zaman
    bakanlık açıklamasını aynen aktarır. "resmi_ile_ayni" sütunu bunu ölçer: bir sayı,
    herhangi bir tarihteki resmi iddiayla birebir aynıysa 1'dir. Bu oran yüksekse
    kalabalık bağımsız değil, resmi iddianın yankısıdır.

Kullanım:
    python scripts/medya_sayi_cikar.py
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
GDELT = KOK / "data" / "raw" / "gdelt"

# ----------------------------------------------------------------------------
# Sözlükler
# ----------------------------------------------------------------------------
SAYI_KELIME = {
    # İngilizce
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100,
    # Türkçe
    "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9,
    "on": 10, "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50, "yüz": 100,
}

# Sıra önemli: önce özel (birleşik) kalıplar
KATEGORI_KALIP = [
    ("zirhli_toplam", r"tanks? and (?:other )?armou?red|tanks? and (?:other )?vehicles|zırhlı araç(?:lar)? ve tank|tank ve zırhlı"),
    ("hava_savunma", r"air[- ]defen[cs]e|s-300|\bosa\b|\bsam\b|anti-aircraft|hava savunma"),
    ("roketatar", r"rocket launcher|\bmlrs\b|multiple[- ]launch|\bgrad\b|smerch|roketatar|çok namlulu"),
    ("topcu", r"artillery|howitzer|\bcannons?\b|mortars?\b|topçu|obüs|\bhavan"),
    # "armored vehicles" medyada genelde tankları da kapsar (Ermeni iddiaları böyle) -> zirhli_toplam
    ("zirhli_arac", r"armou?red (?:combat |personnel )(?:vehicle|carrier)|\bapcs?\b|\bbmps?\b|\bifvs?\b"),
    ("zirhli_toplam", r"armou?red (?:vehicle|machine|equipment)|zırhlı"),
    ("tank", r"\btanks?\b|\btank(?:lar|ı)"),
    ("iha", r"drones?\b|\buavs?\b|unmanned|bayraktar|harop|\biha\b|insansız"),
    ("helikopter", r"helicopters?|helikopter"),
    ("ucak", r"aircraft|warplanes?|\bplanes?\b|\bjets?\b|su-25|uçak"),
    ("radar", r"radars?"),
    ("lojistik", r"trucks?|lorr(?:y|ies)|kamyon"),
    ("sivil_olu", r"civilians?|sivil"),
    # Suriyeli paralı asker iddiaları ayrı tutulur (ordu kaybı değil)
    ("parali_asker", r"syrian|mercenar|jihadi|paralı"),
    ("asker_olu", r"soldiers?|servicem[ae]n|troops|militants?|fighters|personnel|manpower|military (?:deaths|dead|casualties)"
                  r"|asker|şehit|etkisiz hale"),
    # Kim olduğu belli olmayan ölüler ("people were killed", "dead")
    ("genel_olu", r"people|persons|casualt|death toll|\bkilled\b|\bdead\b|öldürül"),
]

# "tens of thousands", "hundreds of people" gibi kalıplar GKG'de 10000 / 100 olarak sayıya dönüşüyor -> at
KALIP_IFADE = re.compile(r"^(?:of )?(?:tens |hundreds |dozens |scores )?(?:of )?(?:thousands|hundreds|dozens|millions)\b", re.I)
YAPI = re.compile(r"facilit|house|building|home|settlement|village|school|hospital|infrastructure|bina|ev\b|köy|tesis", re.I)

# Haber sitesinin hangi tarafın iddialarını aktardığı (hizalama).
# .am siteleri ve Ermeni diaspora yayınları -> Ermeni iddiaları; .az ve Türk siteleri -> Azerbaycan iddiaları.
# Big News Network gibi toplayıcılar (azerbaijannews.net, afghanistansun.com...) tarafsız sayılır.
ERMENI_SITE = re.compile(r"\.am$|asbarez|armenianweekly|mirrorspectator|panarmenian|massispost|armenpress|civilnet"
                         r"|horizonweekly|armradio|hetq|azatutyun|evnreport|armenianow|aravot|lragir|arka\.am", re.I)
AZERI_TURK_SITE = re.compile(r"\.az$|\.tr$|azernews|aze\.media|caspiannews|azertag|apa\.az|trend\.az|report\.az"
                             r"|yenisafak|dailysabah|trtworld|hurriyet|sabah|haberturk|aksam|milliyet|anews"
                             r"|haber7|ensonhaber|yeniakit|turkiyegazetesi|aydinlik|sozcu|cumhuriyet", re.I)
DUSMAN = re.compile(r"enemy|hostile|adversar|occup|opponent|düşman|işgalci", re.I)
KENDI = re.compile(r"\bits\b|\btheir\b|\bour\b|\bown\b", re.I)
EKIPMAN = {"tank", "zirhli_arac", "zirhli_toplam", "topcu", "roketatar", "hava_savunma", "iha",
           "helikopter", "ucak", "radar", "lojistik"}


DIL_HIZALAMA = {"hye": "Ermenistan", "tur": "Azerbaycan", "aze": "Azerbaycan", "axe": "Azerbaycan"}


def site_hizalama(domain, dil=None):
    """Önce site adına, bulamazsa haberin diline bakar (Ermenice -> Ermeni; Türkçe/Azerice -> Azeri-Türk)."""
    d = str(domain).lower()
    if not (ERMENI_SITE.search(d) or AZERI_TURK_SITE.search(d)) and dil in DIL_HIZALAMA:
        return DIL_HIZALAMA[dil]
    if ERMENI_SITE.search(d):
        return "Ermenistan"
    if AZERI_TURK_SITE.search(d):
        return "Azerbaycan"
    return None
KATEGORI_KALIP = [(k, re.compile(p, re.I)) for k, p in KATEGORI_KALIP]

TARAF_SIFAT = {
    "Ermenistan": re.compile(r"armenian|armenia's|karabakh(?:'s)? (?:army|forces|military)|artsakh|separatist|ermeni", re.I),
    "Azerbaycan": re.compile(r"azerbaijani|azeri|azerbaijan's|azerbaycan(?:'ın|lı)?|azeri", re.I),
}
IDDIA_EDEN = {
    "Azerbaycan": re.compile(r"azerbaijan(?:i)?(?: defen[cs]e)?(?: ministry| mod)? (?:says|said|claims?|reports?)"
                             r"|baku (?:says|claims)|aliyev|azerbaycan (?:msb|savunma)|azerbaycan.{0,30}(?:açıkla|duyur)", re.I),
    "Ermenistan": re.compile(r"armenia(?:n)?(?: defen[cs]e)?(?: ministry| mod)? (?:says|said|claims?|reports?)"
                             r"|yerevan (?:says|claims)|pashinyan|karabakh (?:says|army|officials|authorities)|artsakh"
                             r"|ermenistan (?:savunma|açıkla)", re.I),
}
KARSI = {"Azerbaycan": "Ermenistan", "Ermenistan": "Azerbaycan"}

SAYI_DESEN = r"\b(\d{1,3}(?:[,.]\d{3})+|\d+|" + "|".join(sorted(SAYI_KELIME, key=len, reverse=True)) + r")\b"


def sayi_coz(s):
    s = s.lower()
    if s in SAYI_KELIME:
        return SAYI_KELIME[s]
    try:
        return int(re.sub(r"[,.]", "", s))
    except ValueError:
        return None


def kategori_bul(metin):
    """Metinde sayıya EN YAKIN (en önce geçen) kategori sözcüğünü döndürür."""
    en_iyi, en_iyi_konum = None, None
    for kat, desen in KATEGORI_KALIP:   # eşitlikte listedeki sıra kazanır
        m = desen.search(metin)
        if m and (en_iyi_konum is None or m.start() < en_iyi_konum):
            en_iyi, en_iyi_konum = kat, m.start()
    return en_iyi


def taraf_bul(metin):
    bulunan = [t for t, d in TARAF_SIFAT.items() if d.search(metin)]
    return bulunan[0] if len(bulunan) == 1 else None


def iddia_eden_bul(baslik):
    bulunan = [t for t, d in IDDIA_EDEN.items() if d.search(baslik)]
    return bulunan[0] if len(bulunan) == 1 else None


def basliktan_cikar(baslik):
    """Bir başlıktaki (adet, kategori, kayıp_taraf, iddia_eden) dörtlülerini döndürür."""
    if not isinstance(baslik, str):
        return []
    sonuc = []
    iddia_eden = iddia_eden_bul(baslik)
    for m in re.finditer(SAYI_DESEN, baslik, re.I):
        adet = sayi_coz(m.group(1))
        if adet is None or adet == 0 or 1990 <= adet <= 2030:   # yılları ele
            continue
        # sayının hemen önü "on" ise Türkçe "on" ile İngilizce edatı karıştırma
        if m.group(1).lower() == "on":
            continue
        # sayıdan sonraki ~6 kelime: sayılan nesne burada olmalı
        sonra = " ".join(baslik[m.end():].split()[:6])
        kat = kategori_bul(sonra)
        if kat is None:
            # sayı sonda: "death toll among its soldiers rises to 1,177", "losses reach 300"
            once = " ".join(baslik[:m.start()].split()[-7:])
            if re.search(r"(?:rises?|risen|climbs?|reach(?:es)?|stands?|hits?|now|at|to)\s*$", once, re.I):
                kat = kategori_bul(once)
                sonra = once
        if kat is None:
            continue
        # asker_olu için "killed"/"dead" sayıdan SONRA gelmeli ("40 killed", "40 soldiers killed")
        pencere = sonra
        taraf = taraf_bul(pencere)
        if taraf is None and iddia_eden:
            # "Azerbaijan says it destroyed 30 tanks" -> kayıp karşı tarafın
            # "Armenia says 40 of its soldiers killed" -> kayıp kendi tarafının
            if kat in ("asker_olu",) and re.search(r"\bits\b|\bown\b|\bour\b|death toll", baslik, re.I):
                taraf = iddia_eden
            else:
                taraf = KARSI[iddia_eden]
        sonuc.append((adet, kat, taraf, iddia_eden))
    return sonuc




def gkg_satiri(nesne, kaynak_alan, domain, dil=None):
    """GKG sayı satırından (kategori, kayıp_taraf, iddia_eden) çıkarır. Kullanılamazsa kategori None."""
    if not isinstance(nesne, str):
        return None, None, None   # nesnesi boş sayımlar (ör. KILL#43#) belirsiz: atılır
    if YAPI.search(nesne) or KALIP_IFADE.search(nesne.strip()):
        return None, None, None   # "290 civilian facilities", "tens of thousands of casualties"
    kat = kategori_bul(nesne)
    if kat is None and str(kaynak_alan).startswith("count_KILL"):
        kat = "genel_olu"
    hiz = site_hizalama(domain, dil)
    taraf = taraf_bul(nesne)
    if taraf is None and hiz:
        if DUSMAN.search(nesne) or kat in EKIPMAN:
            # Ermeni sitesinde "tanks" / "enemy helicopters" -> Azerbaycan'ın kaybı (ve tersi)
            taraf = KARSI[hiz]
        elif kat == "asker_olu" and KENDI.search(nesne):
            # "of its servicemen", "their troops" -> sitenin kendi tarafı açıklıyor
            taraf = hiz
    return kat, taraf, hiz


def medya_grubu(hiz):
    return {"Ermenistan": "Ermeni medyası", "Azerbaycan": "Azeri-Türk medyası"}.get(hiz, "uluslararası")


# ----------------------------------------------------------------------------
def main():
    satirlar = []

    doc_yol = GDELT / "doc_makaleler.csv"
    if doc_yol.exists():
        doc = pd.read_csv(doc_yol).drop_duplicates(subset="url")
        print(f"DOC: {len(doc)} benzersiz makale")
        for r in doc.itertuples():
            for adet, kat, taraf, iddia in basliktan_cikar(r.baslik):
                satirlar.append({
                    "tarih": pd.to_datetime(str(r.gorulme_zamani)[:8], format="%Y%m%d", errors="coerce"),
                    "kaynak_turu": "baslik", "domain": r.domain, "url": r.url, "dil": r.dil,
                    "adet": adet, "proje_kategori": kat, "kayip_taraf": taraf,
                    "iddia_eden": iddia or site_hizalama(r.domain), "metin": r.baslik,
                })
    else:
        print(f"(yok) {doc_yol}")

    gkg_yol = GDELT / "gkg_sayilar.csv"
    if gkg_yol.exists():
        gkg = pd.read_csv(gkg_yol)
        print(f"GKG: {len(gkg)} sayı satırı, {gkg.url.nunique()} makale")
        for r in gkg.itertuples():
            kat, taraf, hiz = gkg_satiri(r.nesne, r.kaynak_alan, r.domain, r.kaynak_dil)
            if kat is None or not (1 <= r.adet <= 100000) or 1990 <= r.adet <= 2030:
                continue
            satirlar.append({
                "tarih": pd.to_datetime(str(r.tarih_saat)[:8], format="%Y%m%d", errors="coerce"),
                "kaynak_turu": "gkg", "domain": r.domain, "url": r.url,
                "dil": r.kaynak_dil if isinstance(r.kaynak_dil, str) else "eng",
                "adet": int(r.adet), "proje_kategori": kat, "kayip_taraf": taraf, "iddia_eden": hiz,
                "metin": r.nesne,
            })
    else:
        print(f"(yok) {gkg_yol}")

    if not satirlar:
        print("Hiç girdi yok. Önce gdelt_gkg_indir.py'yi çalıştır.")
        return

    med = pd.DataFrame(satirlar)
    # Aynı makale aynı sayıyı birden çok kez verdiyse (başlık + metin, ya da GKG tekrarı) bir kez say
    med = med.drop_duplicates(subset=["url", "adet", "proje_kategori"])
    med["medya_grubu"] = med.iddia_eden.map(medya_grubu)

    # --- Yankı ölçümü: sayı, herhangi bir resmi iddiayla birebir aynı mı? ---
    iddia = pd.read_csv(KOK / "data" / "raw" / "resmi_iddialar.csv", parse_dates=["tarih"])
    # Tek tek satırlar + aynı gün imha+ele geçirilen toplamları (ör. 366 tank = imha + ele geçirilen)
    gun_top = iddia.groupby(["tarih", "kayip_taraf", "proje_kategori"]).adet.sum().reset_index()
    resmi_set = set(zip(iddia.kayip_taraf, iddia.adet.astype(int))) | set(zip(gun_top.kayip_taraf, gun_top.adet.astype(int)))
    # Kategori bilerek kontrol edilmiyor: medya "armored vehicles" ile resmi "tanks and armored" aynı sayıyı verebilir.
    # Not: resmi_iddialar.csv her günün iddiasını içermediği için bu oran yankının ALT sınırıdır.
    med["resmi_ile_ayni"] = [int((t, a) in resmi_set) if isinstance(t, str) else 0
                             for t, a in zip(med.kayip_taraf, med.adet)]

    sutunlar = ["tarih", "kaynak_turu", "domain", "medya_grubu", "url", "dil", "adet", "proje_kategori",
                "kayip_taraf", "iddia_eden", "resmi_ile_ayni", "metin"]
    med = med[sutunlar].sort_values("tarih")
    (KOK / "data" / "clean").mkdir(parents=True, exist_ok=True)
    med.to_csv(KOK / "data" / "clean" / "medya_iddialari.csv", index=False, encoding="utf-8")
    print(f"-> data/clean/medya_iddialari.csv: {len(med)} sayı, {med.domain.nunique()} site, "
          f"{med.kayip_taraf.notna().sum()} tanesinde kayıp tarafı belli")

    # --- Kalabalık tahmini: site başına en büyük sayı -> siteler arası medyan ---
    taraf_belli = med.dropna(subset=["kayip_taraf"])
    taraf_belli = taraf_belli[taraf_belli.proje_kategori.isin(EKIPMAN | {"asker_olu"})]
    site_tahmin = taraf_belli.groupby(["kayip_taraf", "proje_kategori", "medya_grubu", "domain"]).adet.max().reset_index()

    def geo(x):
        return float(np.exp(np.log(x).mean()))

    def ozetle(df, gruplar):
        return (df.groupby(gruplar).adet
                .agg(site_sayisi="count", kalabalik_medyan="median", kalabalik_geo_ort=geo,
                     en_kucuk="min", en_buyuk="max").reset_index())

    hepsi = ozetle(site_tahmin, ["kayip_taraf", "proje_kategori"]).assign(medya_grubu="HEPSİ")
    gruplu = ozetle(site_tahmin, ["kayip_taraf", "proje_kategori", "medya_grubu"])
    ozet = pd.concat([hepsi, gruplu], ignore_index=True)
    yanki = pd.concat([
        taraf_belli.groupby(["kayip_taraf", "proje_kategori"]).resmi_ile_ayni.mean().reset_index().assign(medya_grubu="HEPSİ"),
        taraf_belli.groupby(["kayip_taraf", "proje_kategori", "medya_grubu"]).resmi_ile_ayni.mean().reset_index(),
    ]).rename(columns={"resmi_ile_ayni": "resmi_ile_ayni_oran"})
    ozet = ozet.merge(yanki, how="left")

    # Resmi iddia: karşı tarafın o kategoride verdiği son (en yüksek) sayı
    imha_ele = iddia[iddia.durum.isin(["imha", "ele_gecirildi"])]
    gunluk = imha_ele.groupby(["kayip_taraf", "proje_kategori", "tarih"]).adet.sum().reset_index()
    son_resmi = gunluk.groupby(["kayip_taraf", "proje_kategori"]).adet.max().rename("resmi_iddia_son").reset_index()
    # Ermeni tarafı tank+zırhlıyı tek sayı veriyor: medya "tank" dediğinde de bu sayıyla kıyaslanır
    ek = son_resmi[son_resmi.proje_kategori == "zirhli_toplam"].assign(proje_kategori="tank")
    son_resmi = pd.concat([son_resmi, ek[~ek.set_index(["kayip_taraf", "proje_kategori"]).index.isin(
        son_resmi.set_index(["kayip_taraf", "proje_kategori"]).index)]])
    ozet = ozet.merge(son_resmi, how="left")

    # Gerçeğe en yakın referans: ekipman için Oryx (alt sınır), asker ölüsü için UCDP en iyi tahmin
    oryx = pd.read_csv(KOK / "data" / "clean" / "oryx_karabag_ozet.csv")
    ucdp = pd.read_csv(KOK / "data" / "clean" / "ucdp_karabag.csv")

    def oryx_say(taraf, kat):
        d = oryx[oryx.kayip_taraf == taraf]
        hava = d[d.proje_kategori == "hava_araci"]
        if kat == "helikopter":
            return hava[hava.model.str.contains("Mi-")].adet.sum()
        if kat == "ucak":
            return hava[~hava.model.str.contains("Mi-|An-2")].adet.sum()   # An-2 = yem olarak kullanılan eski uçak
        esle = {"zirhli_toplam": ["tank", "zirhli_arac"]}.get(kat, [kat])
        return d[d.proje_kategori.isin(esle)].adet.sum()

    ucdp_olu = {"Azerbaycan": ucdp.deaths_a.sum(), "Ermenistan": ucdp.deaths_b.sum()}
    ozet["referans"] = [ucdp_olu[t] if k == "asker_olu" else oryx_say(t, k)
                        for t, k in zip(ozet.kayip_taraf, ozet.proje_kategori)]
    ozet["referans_kaynak"] = np.where(ozet.proje_kategori == "asker_olu", "UCDP", "Oryx")
    ozet["kalabalik_bolu_ref"] = (ozet.kalabalik_medyan / ozet.referans.replace(0, np.nan)).round(2)
    ozet["resmi_bolu_ref"] = (ozet.resmi_iddia_son / ozet.referans.replace(0, np.nan)).round(2)
    ozet = ozet.sort_values(["kayip_taraf", "proje_kategori", "medya_grubu"])

    (KOK / "results").mkdir(exist_ok=True)
    ozet.round(2).to_csv(KOK / "results" / "medya_ozet.csv", index=False, encoding="utf-8")
    print("-> results/medya_ozet.csv")
    with pd.option_context("display.width", 250, "display.max_columns", 20):
        print(ozet.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
