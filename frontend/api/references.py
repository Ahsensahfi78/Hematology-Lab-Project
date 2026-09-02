"""Parameter metadata, default reference ranges, units, and auto-calc rules.

Two panel types are supported:
  - TYPE_LMG: WBC diff as Lymph/Mid/Gran (%).  Gran% displayed.
  - TYPE_NEU: WBC diff as Neu/Lymph/Mono/Eoso/Baso (%).
"""

PANEL_TYPE_LMG = "LMG"
PANEL_TYPE_NEU = "NEU"

# (key, label, default unit)
# Groups: wbc, rbc, plt
PARAMETERS = [
    # WBC group
    ("wbc", "WBC (Total White Blood Cell Count)", "x10^3/uL", "wbc"),
    ("lymph_pct", "Lymphocytes (%)", "%", "wbc"),
    ("mid_pct", "Mid Cells (%)", "%", "wbc"),
    ("gran_pct", "Granulocytes (%)", "%", "wbc"),
    ("lymph_abs", "Lymphocytes (Absolute)", "/uL", "wbc"),
    ("mid_abs", "Mid Cells (Absolute)", "/uL", "wbc"),
    ("gran_abs", "Granulocytes (Absolute)", "/uL", "wbc"),
    ("neu_pct", "Neutrophils (%)", "%", "wbc"),
    ("mono_pct", "Monocytes (%)", "%", "wbc"),
    ("eoso_pct", "Eosinophils (%)", "%", "wbc"),
    ("baso_pct", "Basophils (%)", "%", "wbc"),
    # RBC group
    ("rbc", "RBC (Red Blood Cell Count)", "M/uL", "rbc"),
    ("hgb", "HGB (Haemoglobin)", "g/dL", "rbc"),
    ("hct", "HCT (Haematocrit)", "%", "rbc"),
    ("mcv", "MCV (Mean Corpuscular Volume)", "fL", "rbc"),
    ("mch", "MCH (Mean Corpuscular Hb)", "pg", "rbc"),
    ("mchc", "MCHC (Mean Corpuscular Hb Conc.)", "g/dL", "rbc"),
    ("rdw_cv", "RDW-CV", "%", "rbc"),
    ("rdw_sd", "RDW-SD", "fL", "rbc"),
    # PLT group
    ("plt", "PLT (Platelet Count)", "x10^3/uL", "plt"),
    ("mpv", "MPV (Mean Platelet Volume)", "fL", "plt"),
    ("pdw", "PDW (Platelet Distribution Width)", "%", "plt"),
    ("pct", "PCT (Platelet Crit)", "%", "plt"),
]

PARAM_BY_KEY = {k: (label, unit, group) for k, label, unit, group in PARAMETERS}

# Friendly descriptions for tooltips (non-technical)
PARAM_DESCRIPTIONS = {
    "wbc": "Total number of white blood cells, which fight infection.",
    "lymph_pct": "Lymphocytes as a % of white cells (immune cells).",
    "mid_pct": "Mid-sized cells (monocytes/eosinophils/basophils) as a %.",
    "gran_pct": "Granulocytes (neutrophils etc.) as a % of white cells.",
    "neu_pct": "Neutrophils (main bacteria-fighting cells) as a %.",
    "mono_pct": "Monocytes (scavenger cells) as a %.",
    "eoso_pct": "Eosinophils (allergy/parasite cells) as a %.",
    "baso_pct": "Basophils as a % (smallest share of white cells).",
    "rbc": "Red blood cells that carry oxygen around the body.",
    "hgb": "The oxygen-carrying protein inside red blood cells.",
    "hct": "The % of your blood made up of red blood cells.",
    "mcv": "Average size of a red blood cell.",
    "mch": "Average amount of haemoglobin in a single red blood cell.",
    "mchc": "Average concentration of haemoglobin in red blood cells.",
    "rdw_cv": "How much red blood cells vary in size (CV method).",
    "rdw_sd": "How much red blood cells vary in size (SD method).",
    "plt": "Platelets, which help blood to clot.",
    "mpv": "Average size of platelets.",
    "pdw": "How much platelets vary in size.",
    "pct": "The % of blood volume made up of platelets.",
}

# Default adult reference ranges and units.
# Values in raw units; for 10^3 type params we store the raw numeric.
# Ranges per gender where relevant.
ADULT_REFS = {
    "male": {
        "wbc": (4.0, 11.0),
        "lymph_pct": (20.0, 45.0),
        "mid_pct": (3.0, 12.0),
        "gran_pct": (45.0, 70.0),
        "lymph_abs": (1000.0, 4800.0),
        "mid_abs": (200.0, 1200.0),
        "gran_abs": (2500.0, 7000.0),
        "neu_pct": (40.0, 75.0),
        "mono_pct": (2.0, 10.0),
        "eoso_pct": (1.0, 6.0),
        "baso_pct": (0.0, 2.0),
        "rbc": (4.5, 5.9),
        "hgb": (13.5, 18.0),
        "hct": (40.0, 54.0),
        "mcv": (80.0, 100.0),
        "mch": (27.0, 33.0),
        "mchc": (32.0, 36.0),
        "rdw_cv": (11.5, 14.5),
        "rdw_sd": (37.0, 54.0),
        "plt": (150.0, 450.0),
        "mpv": (7.4, 10.4),
        "pdw": (9.0, 17.0),
        "pct": (0.15, 0.40),
    },
    "female": {
        "wbc": (4.0, 11.0),
        "lymph_pct": (20.0, 45.0),
        "mid_pct": (3.0, 12.0),
        "gran_pct": (45.0, 70.0),
        "lymph_abs": (1000.0, 4800.0),
        "mid_abs": (200.0, 1200.0),
        "gran_abs": (2500.0, 7000.0),
        "neu_pct": (40.0, 75.0),
        "mono_pct": (2.0, 10.0),
        "eoso_pct": (1.0, 6.0),
        "baso_pct": (0.0, 2.0),
        "rbc": (4.0, 5.2),
        "hgb": (12.0, 16.0),
        "hct": (36.0, 48.0),
        "mcv": (80.0, 100.0),
        "mch": (27.0, 33.0),
        "mchc": (32.0, 36.0),
        "rdw_cv": (11.5, 14.5),
        "rdw_sd": (37.0, 54.0),
        "plt": (150.0, 450.0),
        "mpv": (7.4, 10.4),
        "pdw": (9.0, 17.0),
        "pct": (0.15, 0.40),
    },
}


def get_adult_refs(gender: str):
    key = "male" if gender == "Male" else "female"
    return ADULT_REFS.get(key, ADULT_REFS["male"])


# Pediatric (children ~1-12) ranges differ; used when age < 14.
PEDIATRIC_REFS = {
    "wbc": (5.0, 13.0),
    "rbc": (3.9, 5.5),
    "hgb": (11.0, 15.0),
    "hct": (33.0, 44.0),
    "mcv": (78.0, 98.0),
    "mch": (25.0, 33.0),
    "mchc": (31.0, 36.0),
    "plt": (150.0, 450.0),
    "mpv": (7.4, 10.4),
    "pdw": (9.0, 17.0),
    "pct": (0.15, 0.40),
}


def default_ref_for(key: str, age: int, gender: str) -> tuple:
    """Return (low, high) default reference range for a parameter."""
    if age is not None and age < 14 and key in PEDIATRIC_REFS:
        return PEDIATRIC_REFS[key]
    return get_adult_refs(gender).get(key, (None, None))


def compute_flag(value, low, high):
    """Return 'H', 'L', or 'normal' for a value vs range."""
    if value is None or low is None or high is None:
        return "normal"
    if value > high:
        return "H"
    if value < low:
        return "L"
    return "normal"


# Auto-calc rules: derived = func(source lows/highs already computed)
# HCT from RBC x MCV ; MCH from HGB/RBC x10 ; MCHC from HGB/HCT x100
AUTO_CALC = {
    "hct": {"formula": "rbc*mcv", "desc": "HCT ≈ RBC × MCV"},
    "mch": {"formula": "(hgb/rbc)*10", "desc": "MCH ≈ HGB ÷ RBC × 10"},
    "mchc": {"formula": "(hgb/hct)*100", "desc": "MCHC ≈ HGB ÷ HCT × 100"},
}
