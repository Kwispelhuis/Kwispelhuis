#!/usr/bin/env python3
"""
VDM Subgroep → Shopify Product Type + Tags mapping
Gebaseerd op collecties_overzicht.md
"""

SUBGROEP_MAPPING = {
    # VOEDING
    "Droogvoer":                    {"type": "Voeding",             "tags": ["voeding", "droogvoer"]},
    "Natvoer":                      {"type": "Voeding",             "tags": ["voeding", "natvoer"]},

    # SNACKS
    "Snacks Gedroogd":              {"type": "Hondensnacks",        "tags": ["snacks", "Gedroogd"]},
    "Snacks Gist":                  {"type": "Hondensnacks",        "tags": ["snacks", "gist"]},
    "Snacks Hard":                  {"type": "Hondensnacks",        "tags": ["snacks", "hard"]},
    "Snacks Kauw":                  {"type": "Hondensnacks",        "tags": ["snacks", "kauwsnacks"]},
    "Snacks Koek":                  {"type": "Hondensnacks",        "tags": ["snacks", "koek"]},
    "Snacks Zacht":                 {"type": "Hondensnacks",        "tags": ["snacks", "zacht"]},

    # SPEELGOED
    "Speelgoed":                    {"type": "Speelgoed",           "tags": ["speelgoed"]},
    "Apporteerspeelgoed":           {"type": "Speelgoed",           "tags": ["speelgoed", "apporteren"]},
    "Knuffels":                     {"type": "Speelgoed",           "tags": ["speelgoed", "knuffels"]},

    # MANDEN & KUSSENS
    "Bedden/Manden/Kussens":        {"type": "Manden & Kussens",    "tags": []},
    "Bedden/Manden/kussens":        {"type": "Manden & Kussens",    "tags": []},
    "Pantoffels":                   {"type": "Manden & Kussens",    "tags": ["Kussens"]},

    # HALSBANDEN & LIJNEN
    "Halsbanden/Lijnen Leer":       {"type": "Halsbanden & Lijnen", "tags": ["halsbanden", "Leer"]},
    "Halsbanden/Lijnen Nylon":      {"type": "Halsbanden & Lijnen", "tags": ["halsbanden", "Nylon"]},
    "Halsbanden/Lijnen Overig":     {"type": "Halsbanden & Lijnen", "tags": ["halsbanden"]},
    "Halsbanden":                   {"type": "Halsbanden & Lijnen", "tags": ["halsbanden"]},
    "Lijnen":                       {"type": "Halsbanden & Lijnen", "tags": ["halsbanden"]},

    # VERZORGING
    "Shampoo":                      {"type": "Verzorging",          "tags": ["verzorging", "Shampoo"]},
    "Conditioners":                 {"type": "Verzorging",          "tags": ["verzorging", "conditioner"]},
    "Conditioner":                  {"type": "Verzorging",          "tags": ["verzorging", "conditioner"]},
    "Parfum":                       {"type": "Verzorging",          "tags": ["verzorging", "parfum"]},
    "Antistatic":                   {"type": "Verzorging",          "tags": ["verzorging", "Antistatic"]},
    "Volume":                       {"type": "Verzorging",          "tags": ["verzorging", "volume"]},
    "Ontklitters En Ontwollers":    {"type": "Verzorging",          "tags": ["verzorging", "ontklitter"]},
    "Ontklitters en Ontwollers":    {"type": "Verzorging",          "tags": ["verzorging", "ontklitter"]},
    "Poten":                        {"type": "Verzorging",          "tags": ["verzorging", "poten"]},
    "Toiletartikelen":              {"type": "Verzorging",          "tags": ["verzorging"]},
    "Verzorgingsproduct":           {"type": "Verzorging",          "tags": ["verzorging"]},
    "Verzorgingsproducten":         {"type": "Verzorging",          "tags": ["verzorging"]},

    # TRIMMEN & GROOMING
    "Borstels":                     {"type": "Trimgereedschap",     "tags": ["grooming", "Borstels"]},
    "Kammen/Borstels":              {"type": "Trimgereedschap",     "tags": ["grooming", "Kammen"]},
    "Kammen":                       {"type": "Trimgereedschap",     "tags": ["grooming", "Kammen"]},
    "Pinnenborstels":               {"type": "Trimgereedschap",     "tags": ["grooming", "Pinnenborstels"]},
    "Trimaccessoires":              {"type": "Trimgereedschap",     "tags": ["grooming", "Trimaccessoires"]},
    "Trimmessen":                   {"type": "Trimgereedschap",     "tags": ["grooming", "Trimmessen"]},
    "Trimstenen":                   {"type": "Trimgereedschap",     "tags": ["grooming", "Trimstenen"]},

    # GEZONDHEID
    "Bestrijdingsartikelen":        {"type": "Gezondheid",          "tags": ["gezondheid", "vlooien"]},
    "Geneesmiddelen":               {"type": "Gezondheid",          "tags": ["gezondheid", "geneesmiddelen"]},
    "Voedingssupplementen":         {"type": "Gezondheid",          "tags": ["gezondheid", "supplementen"]},

    # VOER- & DRINKBAKKEN
    "Voer/Drinkbakken":             {"type": "Voer- en Drinkbakken","tags": ["bakken"]},
    "Voerbakken":                   {"type": "Voer- en Drinkbakken","tags": ["bakken", "voerbak"]},
    "Drinkbakken":                  {"type": "Voer- en Drinkbakken","tags": ["bakken", "drinkbak"]},

    # TRANSPORT
    "Vervoersbox":                  {"type": "Transport",           "tags": ["transport", "vervoersbox"]},
    "Vervoersboxen":                {"type": "Transport",           "tags": ["transport", "vervoersbox"]},
    "Hondentas":                    {"type": "Transport",           "tags": ["transport", "hondentas"]},
    "Hondentassen":                 {"type": "Transport",           "tags": ["transport", "hondentas"]},
    "Outdoor":                      {"type": "Transport",           "tags": ["transport", "outdoor"]},

    # OVERIG
    "Onderdelen":                   {"type": "Onderdelen",          "tags": ["onderdelen"]},
    "Cadeaubonnen":                 {"type": "Cadeaubonnen",        "tags": ["cadeaubon"]},
    "Zomer":                        {"type": "Seizoen",             "tags": ["seizoen", "zomer"]},
}


def titelherkenning(titel: str, huidige_tags: list, product_type: str) -> list:
    t = titel.lower()
    extra_tags = set()

    # MANDEN & KUSSENS
    if product_type == "Manden & Kussens":
        if any(w in t for w in ["mand", "ligmand", "reismand", "transportmand"]):
            extra_tags.add("Manden")
        if any(w in t for w in ["kussen", "slaapkussen", "hondenku"]):
            extra_tags.add("Kussens")
        bed_woorden = ["hondenbed", "slaapbed", "ligbed", "matras", "ligmat", "donut"]
        if any(w in t for w in bed_woorden):
            extra_tags.add("bedden")
        elif "bed" in t and any(w in t for w in ["hond", "slaap", "lig", "rust"]):
            extra_tags.add("bedden")

    # SPEELGOED
    if product_type == "Speelgoed":
        if any(w in t for w in ["apport", "frisbee", "dummy", "werpbal", "gooi"]):
            extra_tags.add("apporteren")
        if any(w in t for w in ["touw", "rope", "knoop", "vlechttouw"]):
            extra_tags.add("touw")
        if any(w in t for w in ["piep", "squeak", "piepspeelgoed"]):
            extra_tags.add("piep")
        if any(w in t for w in ["interactief", "puzzel", "intelligentie", "slow feeder",
                                  "lickmat", "lick mat", "snuffel", "activity"]):
            extra_tags.add("interactief")
        if any(w in t for w in ["knuffel", "pluche", "plush", "knuffeldier"]):
            extra_tags.add("knuffels")
        if "bal " in t or t.endswith("bal") or "ballen" in t:
            extra_tags.add("apporteren")

    # VOER- & DRINKBAKKEN
    if product_type == "Voer- en Drinkbakken":
        if any(w in t for w in ["drink", "waterbak", "waterkom", "drinkfontein"]):
            extra_tags.add("drinkbak")
        if any(w in t for w in ["voer", "eetbak", "voederbak", "kom ", "bakje"]):
            extra_tags.add("voerbak")
        if "slow" in t or "lick" in t:
            extra_tags.add("voerbak")
            extra_tags.add("interactief")

    # VERZORGING
    if product_type == "Verzorging":
        if any(w in t for w in ["ontklitt", "ontwoll", "mat breaker"]):
            extra_tags.add("ontklitter")
        if any(w in t for w in ["parfum", "spray", "cologne", "bodyspray"]):
            extra_tags.add("parfum")
        if "antistatic" in t or "anti-static" in t:
            extra_tags.add("Antistatic")
        if "volume" in t:
            extra_tags.add("volume")
        if any(w in t for w in ["poot", "poten", "teer", "zool"]):
            extra_tags.add("poten")
        if any(w in t for w in ["shampoo", "wassh"]):
            extra_tags.add("Shampoo")
        if any(w in t for w in ["conditioner", "conditioneer"]):
            extra_tags.add("conditioner")

    alle_tags = list(set(huidige_tags) | extra_tags)
    return alle_tags


def get_mapping(subgroep: str, titel: str = "") -> dict:
    basis = SUBGROEP_MAPPING.get(subgroep, {
        "type": subgroep.title(),
        "tags": [subgroep.lower().replace(' ', '-').replace('/', '-')]
    })

    result = {
        "type": basis["type"],
        "tags": list(basis["tags"])
    }

    if titel:
        result["tags"] = titelherkenning(titel, result["tags"], result["type"])

    return result
