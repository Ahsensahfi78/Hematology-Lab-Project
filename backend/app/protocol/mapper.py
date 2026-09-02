"""Map analyzer/device parameter identifiers to canonical lab parameter keys.

Different analyzers (Sysmex, Beckman, Roche, Mindray, etc.) report parameters
under different codes/abbreviations. This module normalizes an OBX/ASTM
identifier + name into our canonical `parameter_name` used across the app.
"""

import re

# alias -> canonical parameter key
ALIASES = {
    # WBC
    "WBC": "wbc",
    "WBC#": "wbc",
    "LEUK": "wbc",
    # WBC differential (percent + absolute)
    "LYMPH%": "lymph_pct",
    "LYM%": "lymph_pct",
    "LY%": "lymph_pct",
    "LYMPH#": "lymph_abs",
    "LYM#": "lymph_abs",
    "LY#": "lymph_abs",
    "MID%": "mid_pct",
    "MID#": "mid_abs",
    "MONO%": "mono_pct",
    "MONO#": "mono_abs",
    "GRAN%": "gran_pct",
    "GRAN#": "gran_abs",
    "NEU%": "neu_pct",
    "NEUT%": "neu_pct",
    "NEUT#": "neu_abs",
    "EOSO%": "eoso_pct",
    "EO%": "eoso_pct",
    "EOS%": "eoso_pct",
    "BASO%": "baso_pct",
    "BASO#": "baso_abs",
    "BAS%": "baso_pct",
    # RBC
    "RBC": "rbc",
    "RBC#": "rbc",
    "HGB": "hgb",
    "HGB-": "hgb",
    "HEMOGLOBIN": "hgb",
    "HCT": "hct",
    "HCT%": "hct",
    "MCV": "mcv",
    "HCV": "mcv",
    "MCH": "mch",
    "MCHC": "mchc",
    "RDW-CV": "rdw_cv",
    "RDW": "rdw_cv",
    "RDW-SD": "rdw_sd",
    # PLT
    "PLT": "plt",
    "PLT#": "plt",
    "MPV": "mpv",
    "PDW": "pdw",
    "PCT": "pct",
    "PCT%": "pct",
}

# Canonical keys that don't have a numeric/direct analyzer alias but are
# derived; we drop them if not provided by the device.
DERIVED_KEYS = {"hct", "mch", "mchc", "lymph_abs", "mid_abs", "gran_abs"}

# Normalize various spellings for percentage markers
_PCT_RE = re.compile(r"percent|percentage", re.I)


def normalize_ident(identifier: str, name: str = "") -> str:
    """Return canonical parameter key for an analyzer identifier, or ''."""
    if not identifier:
        return ""

    ident = identifier.strip()
    # Exact alias match
    key = ALIASES.get(ident)
    if key:
        return key

    # Try uppercased match
    upper = ident.upper()
    if upper in ALIASES:
        return ALIASES[upper]

    # Try to strip numbers/units like 'WBC1', 'HGB2', 'WBC#'
    base = re.sub(r"[\d#*]+$", "", upper).strip().rstrip("%")
    if base in ALIASES:
        return ALIASES[base]

    # Search in name as fallback (e.g. name contains 'Lymphocytes')
    if name:
        n = _PCT_RE.sub("", name).upper().strip()
        nl = n.lower()
        if "lymph" in nl:
            return "lymph_pct" if "%" in upper or name.strip().endswith("%") or "percent" in n.lower() else "lymph_abs"
        if "granulocyte" in nl or "gran" in name.lower():
            return "gran_pct" if "%" in upper else "gran_abs"
        if "neutrophil" in nl:
            return "neu_pct"
        if "monocyte" in nl:
            return "mono_pct"
        if "eosinophil" in nl:
            return "eoso_pct"
        if "basophil" in nl:
            return "baso_pct"
        if "haemoglobin" in nl or "hemoglobin" in nl:
            return "hgb"
        if "red blood" in nl or name.upper().startswith("RBC"):
            return "rbc"
        if "white blood" in nl or name.upper().startswith("WBC"):
            return "wbc"
        if "platelet" in nl or name.upper().startswith("PLT"):
            return "plt"
        if "haematocrit" in nl or "hematocrit" in nl:
            return "hct"
        if "mean corpuscular vol" in nl or "MCV" in upper:
            return "mcv"
        if "mean corpuscular hb" in nl or "MCH" in upper or "mean corpuscular hem" in nl:
            return "mch"
        if "mchc" in nl:
            return "mchc"
        if "rdw" in nl:
            return "rdw_cv"
        if "mean platelet vol" in nl:
            return "mpv"

    return ""


def is_known(key: str) -> bool:
    return key in ALIASES.values() or key in DERIVED_KEYS or key == "rdw_sd"