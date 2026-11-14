"""
Resmi iddiaları Oryx'in kanıtlanmış kayıplarıyla karşılaştırır.
Girdi : data/raw/resmi_iddialar.csv, data/clean/oryx_karabag_ozet.csv, data/clean/oryx_zaman_serisi.csv
Çıktı : results/iddia_vs_oryx.csv
Abartma oranı = iddia / Oryx. Oryx bir ALT SINIR olduğu için bu oran abartmanın ÜST SINIRIDIR.
"""
import pandas as pd

iddia = pd.read_csv("data/raw/resmi_iddialar.csv", parse_dates=["tarih"])
oryx = pd.read_csv("data/clean/oryx_karabag_ozet.csv")
zs = pd.read_csv("data/clean/oryx_zaman_serisi.csv", parse_dates=["tarih"])

# --- Oryx'i iddia kategorilerine eşle (nihai liste) ---
def oryx_say(taraf, kats=None, oryx_kats=None, model_haric=None):
    d = oryx[oryx.kayip_taraf == taraf]
    if kats: d = d[d.proje_kategori.isin(kats)]
    if oryx_kats: d = d[d.oryx_kategori.isin(oryx_kats)]
    if model_haric: d = d[~d.model.str.contains(model_haric, regex=True)]
    return int(d.adet.sum())

ZIRHLI = ["tank", "zirhli_arac"]
nihai = {
    # (iddia_eden, proje_kategori) -> Oryx nihai sayı
    ("Azerbaycan", "tank"): oryx_say("Ermenistan", ["tank"]),
    ("Azerbaycan", "zirhli_arac"): oryx_say("Ermenistan", ["zirhli_arac"]),
    ("Azerbaycan", "topcu"): oryx_say("Ermenistan", ["topcu"]),
    ("Azerbaycan", "roketatar"): oryx_say("Ermenistan", ["roketatar"]),
    ("Azerbaycan", "hava_savunma"): oryx_say("Ermenistan", oryx_kats=["Surface-To-Air Missile Systems", "(Self-Propelled) Anti-Aircraft Guns"]),
    ("Azerbaycan", "radar"): oryx_say("Ermenistan", oryx_kats=["Radars"]),
    ("Azerbaycan", "iha"): oryx_say("Ermenistan", ["iha"]),
    ("Azerbaycan", "ucak"): oryx_say("Ermenistan", oryx_kats=["Aircraft and Helicopters"], model_haric="Mi-"),
    ("Azerbaycan", "lojistik"): oryx_say("Ermenistan", ["lojistik"]),
    ("Ermenistan", "zirhli_toplam"): oryx_say("Azerbaycan", ZIRHLI),
    ("Ermenistan", "iha"): oryx_say("Azerbaycan", ["iha"]),
    ("Ermenistan", "helikopter"): oryx_say("Azerbaycan", oryx_kats=["Aircraft and Helicopters"]) - oryx_say("Azerbaycan", oryx_kats=["Aircraft and Helicopters"], model_haric="Mi-"),
    ("Ermenistan", "ucak"): oryx_say("Azerbaycan", oryx_kats=["Aircraft and Helicopters"], model_haric="Mi-|An-2"),
    ("Ermenistan", "roketatar"): oryx_say("Azerbaycan", ["roketatar"]),
}

# --- O günkü Oryx (Wayback; iddia tarihine en yakın ÖNCEKİ veya aynı gün kopya) ---
ZS_MAP = {"zirhli_toplam": ZIRHLI, "tank": ["tank"], "zirhli_arac": ["zirhli_arac"], "topcu": ["topcu"],
          "roketatar": ["roketatar"], "iha": ["iha"], "lojistik": ["lojistik"]}
def o_gunku(tarih, kayip_taraf, pk):
    if pk not in ZS_MAP: return None
    d = zs[(zs.kayip_taraf == kayip_taraf) & (zs.tarih <= tarih + pd.Timedelta(days=1))]
    if d.empty: return None
    son = d.tarih.max()
    return int(d[(d.tarih == son) & d.kategori.isin(ZS_MAP[pk])].kumulatif.sum())

# İddiaları (imha + ele geçirildi) topla
g = iddia[iddia.proje_kategori != "zirhli_ek"].groupby(["tarih", "iddia_eden", "kayip_taraf", "proje_kategori"]).adet.sum().reset_index()
g["oryx_o_gun"] = [o_gunku(r.tarih, r.kayip_taraf, r.proje_kategori) for r in g.itertuples()]
g["oryx_nihai"] = [nihai.get((r.iddia_eden, r.proje_kategori)) for r in g.itertuples()]
g["oran_o_gun"] = (g.adet / g.oryx_o_gun).round(2)
g["oran_nihai"] = (g.adet / g.oryx_nihai).round(2)
g.to_csv("results/iddia_vs_oryx.csv", index=False, encoding="utf-8-sig")

pd.set_option("display.width", 160)
print(g.to_string(index=False))
