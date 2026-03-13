#!/usr/bin/env python3
"""
VDM Subgroep → Shopify Product Type + Tags mapping
Inclusief titelherkenning voor verdere opdeling
"""

# ─── SUBGROEP MAPPING ─────────────────────────────────────────────────────────
# Product Type bepaalt in welke hoofdcollectie een product valt
# Tags bepalen subcollecties

SUBGROEP_MAPPING = {
    # VOEDING
    "Droogvoer":                    {"type": "Voeding",             "tags": ["voeding", "droogvoer"]},
    "Natvoer":                      {"type": "Voeding",             "tags": ["voeding", "natvoer"]},
    "Voedingssupplementen":         {"type": "Gezondheid",          "tags": ["gezondheid", "supplementen"]},

    # SNACKS — VDM splitst al op, dus direct de juiste tag meegeven
    "Snacks Gedroogd":              {"type": "Hondensnacks",        "tags": ["snacks", "gedroogd"]},
    "Snacks Gist":                  {"type": "Hondensnacks",        "tags": ["snacks", "gist"]},
    "Snacks Hard":                  {"type": "Hondensnacks",        "tags": ["snacks", "hard"]},
    "Snacks Kauw":                  {"type": "Hondensnacks",        "tags": ["snacks", "kauwsnacks"]},
    "Snacks Koek":                  {"type": "Hondensnacks",        "tags": ["snacks", "koek"]},
    "Snacks Zacht":                 {"type": "Hondensnacks",        "tags": ["snacks", "zacht"]},

    # SPEELGOED — titelherkenning voegt subcategorie tags toe
    "Speelgoed":                    {"type": "Speelgoed",           "tags": ["speelgoed"]},
    "Apporteerspeelgoed":           {"type": "Speelgoed",           "tags": ["speelgoed", "apporteren"]},
    "Knuffels":                     {"type": "Speelgoed",           "tags": ["speelgoed", "knuffels"]},

    # HALSBANDEN & LIJNEN
    "Halsbanden/Lijnen Leer":       {"type": "Halsbanden & Lijnen", "tags": ["halsbanden", "leer"]},
    "Halsbanden/Lijnen Nylon":      {"type": "Halsbanden & Lijnen", "tags": ["halsbanden", "nylon"]},
    "Halsbanden/Lijnen Overig":     {"type": "Halsbanden & Lijnen", "tags": ["halsbanden"]},

    # VERZORGING — titelherkenning voegt subcategorie tags toe
    "Shampoo":                      {"type": "Verzorging",          "tags": ["verzorging", "shampoo"]},
    "Conditioners":                 {"type": "Verzorging",          "tags": ["verzorging", "conditioner"]},
    "Parfum":                       {"type": "Verzorging",          "tags": ["verzorging", "parfum"]},
    "Toiletartikelen":              {"type": "Verzorging",          "tags": ["verzorging"]},
    "Verzorgingsproduct":           {"type": "Verzorging",          "tags": ["verzorging"]},
    "Antistatic":                   {"type": "Verzorging",          "tags": ["verzorging", "antistatic"]},
    "Ontklitters En Ontwollers":    {"type": "Verzorging",          "tags": ["verzorging", "ontklitter"]},
    "Volume":                       {"type": "Verzorging",          "tags": ["verzorging", "volume"]},
    "Poten":                        {"type": "Verzorging",          "tags": ["verzorging", "poten"]},

    # GEZONDHEID
    "Bestrijdingsartikelen":        {"type": "Gezondheid",          "tags": ["gezondheid", "vlooien"]},
    "Geneesmiddelen":               {"type": "Gezondheid",          "tags": ["gezondheid", "geneesmiddelen"]},

    # TRIMMEN & GROOMING
    "Borstels":                     {"type": "Trimgereedschap",     "tags": ["grooming", "borstels"]},
    "Kammen/Borstels":              {"type": "Trimgereedschap",     "tags": ["grooming", "kammen"]},
    "Pinnenborstels":               {"type": "Trimgereedschap",     "tags": ["grooming", "pinnenborstels"]},
    "Trimaccessoires":              {"type": "Trimgereedschap",     "tags": ["grooming", "trimaccessoires"]},
    "Trimmessen":                   {"type": "Trimgereedschap",     "tags": ["grooming", "trimmessen"]},
    "Trimstenen":                   {"type": "Trimgereedschap",     "tags": ["grooming", "trimstenen"]},

    # SLAAP & COMFORT — titelherkenning splitst op in manden/bedden/kussens
    "Bedden/Manden/Kussens":        {"type": "Manden & Kussens",    "tags": ["slapen"]},
    "Pantoffels":                   {"type": "Manden & Kussens",    "tags": ["slapen", "kussens"]},

    # TRANSPORT
    "Vervoersbox":                  {"type": "Transport",           "tags": ["transport", "vervoersbox"]},
    "Hondentas":                    {"type": "Transport",           "tags": ["transport", "hondentas"]},
    "Outdoor":                      {"type": "Transport",           "tags": ["transport", "outdoor"]},

    # VOER- & DRINKBAKKEN — titelherkenning splitst op
    "Voer/Drinkbakken":             {"type": "Voer- en Drinkbakken","tags": ["bakken"]},
    "Voerbakken":                   {"type": "Voer- en Drinkbakken","tags": ["bakken", "voerbak"]},

    # OVERIG
    "Onderdelen":                   {"type": "Onderdelen",          "tags": ["onderdelen"]},
    "Cadeaubonnen":                 {"type": "Cadeaubonnen",        "tags": ["cadeaubon"]},
    "Zomer":                        {"type": "Seizoen",             "tags": ["seizoen", "zomer"]},
    "Hondentas":                    {"type": "Transport",           "tags": ["transport", "hondentas"]},
}


# ─── TITELHERKENNING ──────────────────────────────────────────────────────────
# Werkt op basis van woorddelen (niet hele woorden) — dus "hondenmand" bevat "mand"
# Volgorde is belangrijk: specifieker eerst
# Meerdere tags mogelijk per product (bijv. apporteerbal met piep krijgt beide)

def titelherkenning(titel: str, huidige_tags: list, product_type: str) -> list:
    """
    Voegt extra tags toe op basis van titelherkenning.
    Werkt als aanvulling op de subgroep mapping.
    Geeft de bijgewerkte tags lijst terug.
    """
    t = titel.lower()
    extra_tags = set()

    # ── MANDEN & KUSSENS ──────────────────────────────────────────────────────
    if product_type == "Manden & Kussens":
        # Manden — check woorddelen
        if any(w in t for w in ["mand", "ligmand", "reismand", "transportmand"]):
            extra_tags.add("manden")

        # Kussens
        if any(w in t for w in ["kussen", "slaapkussen", "hondenku"]):
            extra_tags.add("kussens")

        # Bedden — voorzichtig: alleen als "bed" voorkomt in honden/slaap context
        # of als woorddeel van hondenbed, slaapbed, ligbed
        bed_woorden = ["hondenbed", "slaapbed", "ligbed", "matras", "ligmat", "donut"]
        if any(w in t for w in bed_woorden):
            extra_tags.add("bedden")
        elif "bed" in t and any(w in t for w in ["hond", "slaap", "lig", "rust"]):
            extra_tags.add("bedden")

        # Als geen subcategorie herkend: laat het bij hoofdcollectie (handmatig taggen)

    # ── SPEELGOED ─────────────────────────────────────────────────────────────
    if product_type == "Speelgoed":
        # Apporteren — meerdere tags mogelijk (apporteerbal met piep → beide)
        if any(w in t for w in ["apport", "frisbee", "dummy", "werpbal", "gooi"]):
            extra_tags.add("apporteren")

        # Touw
        if any(w in t for w in ["touw", "rope", "knoop", "vlechttouw"]):
            extra_tags.add("touw")

        # Piep — bewust na apporteren zodat combo mogelijk is
        if any(w in t for w in ["piep", "squeak", "piepspeelgoed"]):
            extra_tags.add("piep")

        # Interactief
        if any(w in t for w in ["interactief", "puzzel", "intelligentie", "slow feeder",
                                  "lickmat", "lick mat", "snuffel", "activity"]):
            extra_tags.add("interactief")

        # Knuffels — ook via titel herkennen naast subgroep
        if any(w in t for w in ["knuffel", "pluche", "plush", "knuffeldier"]):
            extra_tags.add("knuffels")

        # Bal apart (voorzichtig vanwege woorddelen)
        if "bal " in t or t.endswith("bal") or "ballen" in t:
            extra_tags.add("apporteren")

    # ── VOER- & DRINKBAKKEN ───────────────────────────────────────────────────
    if product_type == "Voer- en Drinkbakken":
        if any(w in t for w in ["drink", "waterbak", "waterkom", "drinkfontein"]):
            extra_tags.add("drinkbak")
        if any(w in t for w in ["voer", "eetbak", "voederbak", "kom ", "bakje"]):
            extra_tags.add("voerbak")
        # Slowfeeder valt ook onder voerbakken
        if "slow" in t or "lick" in t:
            extra_tags.add("voerbak")
            extra_tags.add("interactief")

    # ── VERZORGING ────────────────────────────────────────────────────────────
    if product_type == "Verzorging":
        if any(w in t for w in ["ontklitt", "ontwoll", "mat breaker"]):
            extra_tags.add("ontklitter")
        if any(w in t for w in ["parfum", "spray", "cologne", "bodyspray"]):
            extra_tags.add("parfum")
        if "antistatic" in t or "anti-static" in t:
            extra_tags.add("antistatic")
        if "volume" in t:
            extra_tags.add("volume")
        if any(w in t for w in ["poot", "poten", "teer", "zool"]):
            extra_tags.add("poten")
        if any(w in t for w in ["shampoo", "wassh"]):
            extra_tags.add("shampoo")
        if any(w in t for w in ["conditioner", "conditioneer"]):
            extra_tags.add("conditioner")

    # Voeg extra tags toe aan bestaande lijst (geen duplicaten)
    alle_tags = list(set(huidige_tags) | extra_tags)
    return alle_tags


# ─── HOOFD FUNCTIE ────────────────────────────────────────────────────────────

def get_mapping(subgroep: str, titel: str = "") -> dict:
    """
    Geeft type en tags terug voor een VDM subgroep.
    Past daarna titelherkenning toe als aanvulling.
    """
    # Fallback als subgroep onbekend
    basis = SUBGROEP_MAPPING.get(subgroep, {
        "type": subgroep.title(),
        "tags": [subgroep.lower().replace(' ', '-').replace('/', '-')]
    })

    # Kopieer zodat origineel niet wordt aangepast
    result = {
        "type": basis["type"],
        "tags": list(basis["tags"])
    }

    # Titelherkenning als aanvulling
    if titel:
        result["tags"] = titelherkenning(titel, result["tags"], result["type"])

    return result
