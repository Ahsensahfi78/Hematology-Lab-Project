from datetime import datetime

from . import references


def generate_patient_id(session) -> str:
    """Generate a unique, human-friendly patient ID like PT-000123."""
    from sqlalchemy import func

    from .models import Patient

    count = session.query(func.count(Patient.id)).scalar() or 0
    base = int(count) + 1
    # Ensure uniqueness by scanning upward if collision
    candidate = f"PT-{base:06d}"
    while session.query(Patient).filter(Patient.patient_id == candidate).first():
        base += 1
        candidate = f"PT-{base:06d}"
    return candidate


def generate_sample_id(session) -> str:
    """Sample ID auto-incrementing per day: S-YYYYMMDD-###"""
    from sqlalchemy import func
    from sqlalchemy.sql import extract

    from .models import Report

    now = datetime.now()
    day_prefix = now.strftime("%Y%m%d")
    count = (
        session.query(func.count(Report.id))
        .filter(
            extract("year", Report.created_at) == now.year,
            extract("month", Report.created_at) == now.month,
            extract("day", Report.created_at) == now.day,
        )
        .scalar()
        or 0
    )
    seq = int(count) + 1
    # Ensure uniqueness
    candidate = f"S-{day_prefix}-{seq:03d}"
    while (
        session.query(Report)
        .filter(Report.sample_id == candidate)
        .first()
    ):
        seq += 1
        candidate = f"S-{day_prefix}-{seq:03d}"
    return candidate


def build_results_with_defaults(panel_type: str, age: int, gender: str):
    """Return a list of result dicts pre-filled with default units/ranges."""
    refs = references
    results = []
    for key, label, unit, group in refs.PARAMETERS:
        if panel_type == refs.PANEL_TYPE_NEU and key in {
            "mid_pct",
            "gran_pct",
            "mid_abs",
            "gran_abs",
        }:
            continue
        if panel_type == refs.PANEL_TYPE_LMG and key in {
            "neu_pct",
            "mono_pct",
            "eoso_pct",
            "baso_pct",
        }:
            continue
        low, high = refs.default_ref_for(key, age, gender)
        results.append(
            {
                "parameter_name": key,
                "result_value": None,
                "unit": unit,
                "ref_range_low": low,
                "ref_range_high": high,
                "flag": "normal",
            }
        )
    return results


def compute_verification_status(results, current_status="auto_verified"):
    """Auto-verification rules for a report.

    - Any result flagged H/L  -> `pending_review` (needs pathologist sign-off).
    - All results normal      -> `auto_verified`.
    - A report already `reviewed`/`revised` by a pathologist is not downgraded.
    """
    has_abnormal = any((r.flag or "normal") in ("H", "L") for r in results)
    if current_status in ("reviewed", "revised"):
        return current_status
    return "pending_review" if has_abnormal else "auto_verified"
