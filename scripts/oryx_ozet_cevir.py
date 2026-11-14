"""
Tarayıcıdan alınan kodlu Oryx özetini (data/raw/oryx_ozet_kodlu.txt) okunabilir CSV'ye çevirir.
Her satır: taraf | Oryx kategorisi | model | durum metni | adet
Ek sütunlar: proje kategorisi, sade durum (imha/hasarlı/ele_gecirildi/terk), vuran silah.
Kaynak: oryxspioenkop.com 2020 Karabağ listesi, 6 Kasım 2026'da okundu.
"""
import re
import pandas as pd

TARAF = {"E": "Ermenistan", "A": "Azerbaycan"}
KAT = ["Tanks", "Armoured Fighting Vehicles", "Infantry Fighting Vehicles",
       "Armoured Personnel Carriers", "Self-Propelled Anti-tank Missile Systems",
       "Command Posts And Communications Stations", "Engineering Vehicles",
       "Artillery Support Vehicles", "Towed Artillery", "Self-Propelled Artillery",
       "Multiple Rocket Launchers", "Ballistic Missiles", "Mortars",
       "(Self-Propelled) Anti-Aircraft Guns", "Surface-To-Air Missile Systems", "Radars",
       "Jammers and Deception Systems", "Aircraft and Helicopters", "Unmanned Aerial Vehicles",
       "Trucks, Vehicles and Jeeps", "Decoys",
       "Mine-Resistant Ambush Protected (MRAP) Vehicles", "Infantry Mobility Vehicles"]
DURUM = ["destroyed by loitering munition", "destroyed by Spike ATGM", "destroyed by TB2",
         "destroyed by TB2 and artillery", "destroyed by TB2 and Spike ATGM", "destroyed",
         "damaged by TB2", "damaged by Spike ATGM", "damaged and captured", "captured",
         "damaged by loitering munition and captured", "damaged by Spike ATGM and captured",
         "damaged", "damaged by TB2 and captured", "with ZU-23 AA gun, captured",
         "destroyed after capture by Armenia", "abandoned", "unknown", "crashed",
         "with ZU-23 AA gun, destroyed", "damaged and captured", "damaged and abandoned",
         "destroyed by Azerbaijan to prevent capture",
         "captured by Armenia, but later destroyed by Azerbaijan",
         "damaged by loitering munition", "loss admitted by Azerbaijan"]
PROJE_KAT = {
    "Tanks": "tank",
    "Armoured Fighting Vehicles": "zirhli_arac", "Infantry Fighting Vehicles": "zirhli_arac",
    "Armoured Personnel Carriers": "zirhli_arac",
    "Mine-Resistant Ambush Protected (MRAP) Vehicles": "zirhli_arac",
    "Infantry Mobility Vehicles": "zirhli_arac",
    "Self-Propelled Anti-tank Missile Systems": "tanksavar",
    "Towed Artillery": "topcu", "Self-Propelled Artillery": "topcu", "Mortars": "topcu",
    "Multiple Rocket Launchers": "roketatar", "Ballistic Missiles": "balistik_fuze",
    "(Self-Propelled) Anti-Aircraft Guns": "hava_savunma",
    "Surface-To-Air Missile Systems": "hava_savunma", "Radars": "hava_savunma",
    "Jammers and Deception Systems": "elektronik_harp",
    "Aircraft and Helicopters": "hava_araci", "Unmanned Aerial Vehicles": "iha",
    "Trucks, Vehicles and Jeeps": "lojistik", "Decoys": "yem",
    "Command Posts And Communications Stations": "diger",
    "Engineering Vehicles": "diger", "Artillery Support Vehicles": "diger",
}


def sade_durum(s):
    if "captured" in s and "destroyed" not in s:
        return "ele_gecirildi"
    if "destroyed" in s or s == "crashed":
        return "imha"
    if "abandoned" in s:
        return "terk"
    if "damaged" in s:
        return "hasarli"
    return "diger"


def silah(s):
    if "TB2" in s:
        return "TB2"
    if "loitering" in s:
        return "dolanan_muhimmat"
    if "Spike" in s:
        return "Spike_ATGM"
    return "belirtilmemis"


rows = []
for line in open("data/raw/oryx_ozet_kodlu.txt", encoding="utf-8"):
    t, k, model, d, n = line.rstrip("\n").split("|")
    durum = DURUM[int(d)]
    rows.append({
        "kayip_taraf": TARAF[t], "oryx_kategori": KAT[int(k)],
        "proje_kategori": PROJE_KAT[KAT[int(k)]], "model": model,
        "oryx_durum": durum, "durum": sade_durum(durum), "vuran_silah": silah(durum),
        "adet": int(n),
    })
df = pd.DataFrame(rows)
df.to_csv("data/clean/oryx_karabag_ozet.csv", index=False, encoding="utf-8-sig")
print("Toplam araç:", df.adet.sum(), "| satır:", len(df))
print("\nTaraf x kategori:")
print(df.pivot_table(index="proje_kategori", columns="kayip_taraf", values="adet", aggfunc="sum", fill_value=0).to_string())
print("\nVuran silahı belirtilen kayıplar (Ermenistan):")
e = df[df.kayip_taraf == "Ermenistan"]
print(e.pivot_table(index="proje_kategori", columns="vuran_silah", values="adet", aggfunc="sum", fill_value=0).to_string())
