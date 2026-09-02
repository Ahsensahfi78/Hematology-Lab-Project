# ===== database.py =====

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

import os

# Vercel/Render: use /tmp for ephemeral disk; local: use backend directory.
_DB_DIR = "/tmp" if os.environ.get("VERCEL") or os.environ.get("RENDER") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(_DB_DIR, 'labreports.db')}"
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



# ===== models.py =====

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.orm import relationship
from database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    gender = Column(String, nullable=False)  # Male / Female
    age = Column(Integer, nullable=False)
    patient_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    reports = relationship("Report", back_populates="patient", cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    sample_id = Column(String, index=True, nullable=False)
    test_date = Column(DateTime, server_default=func.now())
    requested_by = Column(String, nullable=True)
    technologist_name = Column(String, nullable=True)
    comments = Column(Text, nullable=True)
    verification_status = Column(String, nullable=True, default="auto_verified")  # auto_verified / pending_review / reviewed
    verification_notes = Column(Text, nullable=True)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    source = Column(String, nullable=True)  # manual / hl7 / astm
    created_at = Column(DateTime, server_default=func.now())

    patient = relationship("Patient", back_populates="reports")
    results = relationship(
        "Result", back_populates="report", cascade="all, delete-orphan"
    )


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    parameter_name = Column(String, nullable=False)
    result_value = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    ref_range_low = Column(Float, nullable=True)
    ref_range_high = Column(Float, nullable=True)
    flag = Column(String, nullable=True)  # H / L / normal

    report = relationship("Report", back_populates="results")



# ===== references.py =====

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
    "hct": {"formula": "rbc*mcv", "desc": "HCT â‰ˆ RBC Ã— MCV"},
    "mch": {"formula": "(hgb/rbc)*10", "desc": "MCH â‰ˆ HGB Ã· RBC Ã— 10"},
    "mchc": {"formula": "(hgb/hct)*100", "desc": "MCHC â‰ˆ HGB Ã· HCT Ã— 100"},
}



# ===== schemas.py =====

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class PatientCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    gender: str  # Male / Female
    age: int = Field(ge=0, le=120)

    @field_validator("gender")
    @classmethod
    def check_gender(cls, v):
        if v not in ("Male", "Female"):
            raise ValueError("gender must be 'Male' or 'Female'")
        return v


class PatientOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    gender: str
    age: int
    patient_id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResultIn(BaseModel):
    parameter_name: str
    result_value: Optional[float] = None
    unit: Optional[str] = None
    ref_range_low: Optional[float] = None
    ref_range_high: Optional[float] = None
    flag: Optional[str] = None


class ReportCreate(BaseModel):
    patient_id: int
    requested_by: Optional[str] = None
    technologist_name: Optional[str] = None
    comments: Optional[str] = None
    test_date: Optional[datetime] = None
    panel_type: Optional[str] = "LMG"
    source: Optional[str] = None
    results: List[ResultIn] = []


class ReportUpdate(BaseModel):
    requested_by: Optional[str] = None
    technologist_name: Optional[str] = None
    comments: Optional[str] = None
    test_date: Optional[datetime] = None
    results: Optional[List[ResultIn]] = None


class VerificationUpdate(BaseModel):
    status: str  # auto_verified / revised / reviewed
    verification_notes: Optional[str] = None


class ResultOut(BaseModel):
    id: int
    report_id: int
    parameter_name: str
    result_value: Optional[float] = None
    unit: Optional[str] = None
    ref_range_low: Optional[float] = None
    ref_range_high: Optional[float] = None
    flag: Optional[str] = None

    class Config:
        from_attributes = True


class ReportOut(BaseModel):
    id: int
    patient_id: int
    sample_id: str
    test_date: Optional[datetime] = None
    requested_by: Optional[str] = None
    technologist_name: Optional[str] = None
    comments: Optional[str] = None
    verification_status: Optional[str] = None
    verification_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    patient: Optional[PatientOut] = None
    results: List[ResultOut] = []

    class Config:
        from_attributes = True



# ===== services.py =====

from datetime import datetime

import references


def generate_patient_id(session) -> str:
    """Generate a unique, human-friendly patient ID like PT-000123."""
    from sqlalchemy import func

    from models import Patient

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

    from models import Report

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



# ===== routers/patients.py =====

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Patient
from schemas import PatientCreate, PatientOut
from services import generate_patient_id

router = APIRouter(prefix="/patients", tags=["patients"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    patient = Patient(
        first_name=payload.first_name,
        last_name=payload.last_name,
        gender=payload.gender,
        age=payload.age,
    )
    # Need patient_id assigned -> flush to get id
    db.add(patient)
    patient.patient_id = generate_patient_id(db)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("", response_model=list[PatientOut])
def list_patients(db: Session = Depends(get_db)):
    return db.query(Patient).order_by(Patient.created_at.desc()).all()


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient



# ===== routers/reports.py =====

import io
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Patient, Report, Result
from references import compute_flag, PARAM_DESCRIPTIONS, PARAM_BY_KEY, PARAMETERS
from schemas import ReportCreate, ReportOut, ReportUpdate, VerificationUpdate
from services import generate_sample_id, compute_verification_status

router = APIRouter(prefix="/reports", tags=["reports"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _validate_flag(value):
    if value is None:
        return "normal"
    f = value.strip().upper()
    return f if f in ("H", "L", "NORMAL") else "normal"


def _normalize_key(value):
    return value.strip().lower()


def _load_report(db: Session, report_id: int) -> Report:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("", response_model=ReportOut, status_code=201)
def create_report(payload: ReportCreate, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    report = Report(
        patient_id=payload.patient_id,
        requested_by=payload.requested_by,
        technologist_name=payload.technologist_name,
        comments=payload.comments,
        test_date=payload.test_date or datetime.now(),
        source=payload.source,
    )
    db.add(report)
    # assign sample id before flush so per-day count works
    report.sample_id = generate_sample_id(db)
    db.flush()

    existing = {r.parameter_name for r in report.results}
    results = []
    for item in payload.results:
        key = _normalize_key(item.parameter_name)
        if key in existing:
            continue
        existing.add(key)
        result = Result(
            report_id=report.id,
            parameter_name=key,
            result_value=item.result_value,
            unit=item.unit,
            ref_range_low=item.ref_range_low,
            ref_range_high=item.ref_range_high,
            flag=_validate_flag(item.flag),
        )
        # server-side flag computation as safety net
        if item.flag is None and item.result_value is not None:
            result.flag = compute_flag(
                item.result_value, item.ref_range_low, item.ref_range_high
            )
        db.add(result)
        results.append(result)

    report.verification_status = compute_verification_status(results)

    db.commit()
    db.refresh(report)
    return report


@router.get("", response_model=list[ReportOut])
def list_reports(
    q: str = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Report).join(Patient)
    if q:
        like = f"%{q}%"
        query = query.filter(
            Patient.first_name.ilike(like)
            | Patient.last_name.ilike(like)
            | Patient.patient_id.ilike(like)
            | Report.sample_id.ilike(like)
        )
    return (
        query.order_by(Report.created_at.desc()).limit(min(limit, 500)).all()
    )


@router.get("/queue/review", response_model=list[ReportOut])
def review_queue(db: Session = Depends(get_db)):
    """List reports needing pathologist review (pending_review)."""
    return (
        db.query(Report)
        .filter(Report.verification_status == "pending_review")
        .order_by(Report.created_at.asc())
        .all()
    )


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    return _load_report(db, report_id)


@router.put("/{report_id}", response_model=ReportOut)
def update_report(
    report_id: int, payload: ReportUpdate, db: Session = Depends(get_db)
):
    report = _load_report(db, report_id)
    if payload.requested_by is not None:
        report.requested_by = payload.requested_by
    if payload.technologist_name is not None:
        report.technologist_name = payload.technologist_name
    if payload.comments is not None:
        report.comments = payload.comments
    if payload.test_date is not None:
        report.test_date = payload.test_date

    if payload.results is not None:
        db.query(Result).filter(Result.report_id == report_id).delete()
        db.flush()
        updated_results = []
        for item in payload.results:
            key = _normalize_key(item.parameter_name)
            result = Result(
                report_id=report_id,
                parameter_name=key,
                result_value=item.result_value,
                unit=item.unit,
                ref_range_low=item.ref_range_low,
                ref_range_high=item.ref_range_high,
                flag=_validate_flag(item.flag),
            )
            if item.flag is None and item.result_value is not None:
                result.flag = compute_flag(
                    item.result_value, item.ref_range_low, item.ref_range_high
                )
            db.add(result)
            updated_results.append(result)
        report.verification_status = compute_verification_status(
            updated_results, report.verification_status
        )

    db.commit()
    db.refresh(report)
    return report


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = _load_report(db, report_id)
    db.delete(report)
    db.commit()


@router.post("/{report_id}/verify", response_model=ReportOut)
def verify_report(
    report_id: int,
    payload: VerificationUpdate,
    db: Session = Depends(get_db),
):
    """Pathologist sign-off / release of a report (manual verification).

    status: 'reviewed'  -> released (approved as-is, possibly with notes)
            'revised'   -> edited then released (notes required for edits)
    """
    report = _load_report(db, report_id)
    status = payload.status.strip().lower()
    if status not in ("reviewed", "revised"):
        raise HTTPException(status_code=422, detail="status must be 'reviewed' or 'revised'")

    report.verification_status = status
    report.verification_notes = payload.verification_notes
    report.reviewed_by = "pathologist"
    report.reviewed_at = datetime.now()
    db.commit()
    db.refresh(report)
    return report


def _pdf_escape(text):
    """Escape PDF text (escape backslash/right paren are handled by reportlab)"""
    return text if text is not None else ""


@router.get("/{report_id}/pdf")
def download_pdf(report_id: int, db: Session = Depends(get_db)):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        raise HTTPException(status_code=501, detail="PDF generation not available on this deployment")

    report = _load_report(db, report_id)
    patient = report.patient
    results = sorted(report.results, key=lambda r: _pdf_param_index(r.parameter_name))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=16,
        alignment=1,
        textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"], alignment=1, fontSize=10, textColor=colors.grey
    )
    h_style = ParagraphStyle(
        "Hdr", parent=styles["Normal"], fontSize=9, leading=12
    )
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9)

    story = []
    story.append(Paragraph("HAEMATOLOGY LABORATORY", title_style))
    story.append(
        Paragraph("Fully Automated Haematology Analyzer Report", sub_style)
    )
    story.append(Spacer(1, 4))
    story.append(Paragraph("123 Lab Street - Tel: +0 000 0000", sub_style))
    story.append(Spacer(1, 8))

    # Patient block
    info_data = [
        [
            Paragraph(f"<b>Patient ID:</b> {patient.patient_id}", h_style),
            Paragraph(f"<b>Sample ID:</b> {report.sample_id}", h_style),
        ],
        [
            Paragraph(
                f"<b>Name:</b> {patient.first_name} {patient.last_name}", h_style
            ),
            Paragraph(f"<b>Age:</b> {patient.age}", h_style),
        ],
        [
            Paragraph(f"<b>Gender:</b> {patient.gender}", h_style),
            Paragraph(
                f"<b>Requested By:</b> {report.requested_by or '-'}", h_style
            ),
        ],
        [
            Paragraph(
                f"<b>Test Date:</b> {(report.test_date or report.created_at)}",
                h_style,
            ),
            Paragraph(
                f"<b>Technologist:</b> {report.technologist_name or '-'}", h_style
            ),
        ],
    ]
    info_table = Table(info_data, colWidths=[doc.width / 2, doc.width / 2])
    info_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 10))

    # Results table
    header = [
        Paragraph("<b>Parameter</b>", cell_style),
        Paragraph("<b>Result</b>", cell_style),
        Paragraph("<b>Unit</b>", cell_style),
        Paragraph("<b>Reference Range</b>", cell_style),
        Paragraph("<b>Flag</b>", cell_style),
    ]
    body = [header]
    highlight = []
    for r in results:
        flag = (r.flag or "normal").upper()
        flag_color = "red" if flag == "H" else "blue" if flag == "L" else "green"
        label = PARAM_BY_KEY.get(r.parameter_name, (r.parameter_name, "", ""))[0]
        ref = ""
        if r.ref_range_low is not None or r.ref_range_high is not None:
            ref = f"{r.ref_range_low or '-'} - {r.ref_range_high or '-'}"
        row = [
            Paragraph(label, cell_style),
            Paragraph(f"{r.result_value if r.result_value is not None else '-'}", cell_style),
            Paragraph(f"{r.unit or '-'}", cell_style),
            Paragraph(ref, cell_style),
            Paragraph(f'<font color="{flag_color}">{"" if flag == "NORMAL" else flag}</font>', cell_style),
        ]
        body.append(row)
        if flag in ("H", "L"):
            highlight.append(len(body) - 1)

    res_table = Table(body, colWidths=[doc.width * 0.42, doc.width * 0.14, doc.width * 0.14, doc.width * 0.2, doc.width * 0.1])
    style_cmds = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for row_idx in highlight:
        style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#fef2f2")))
    res_table.setStyle(TableStyle(style_cmds))
    story.append(res_table)
    story.append(Spacer(1, 6))

    if report.comments:
        story.append(
            Paragraph(f"<b>Comments:</b> {report.comments}", h_style)
        )
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            f"______________________________<br/><b>Technologist Signature</b>&nbsp;&nbsp;"
            f"{report.technologist_name or ''}",
            h_style,
        )
    )

    doc.build(story)
    buf.seek(0)
    filename = f"report_{report.sample_id}.pdf"
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _pdf_param_index(key):
    order = {k: i for i, (k, *_ ) in enumerate(PARAMETERS)}
    return order.get(key, 999)



# ===== main.py =====

import os, secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import Base, engine
from routers import patients, reports

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hematology Lab Reports API")

# Fixed single-technician credentials (simple auth)
TECH_USERNAME = "technician"
TECH_PASSWORD = "lab123"

# Simple in-memory token store {token: expiry}
_tokens = {}

# CORS: accept production frontend URL(s) from env, plus local dev defaults.
_extra_origins = os.environ.get("CORS_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "https://hematology-lab-project.vercel.app",
        *[_o.strip() for _o in _extra_origins if _o.strip()],
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str


@app.post("/auth/login", response_model=TokenResponse)
def login(credentials: LoginRequest):
    if (
        credentials.username == TECH_USERNAME
        and credentials.password == TECH_PASSWORD
    ):
        token = secrets.token_urlsafe(32)
        _tokens[token] = datetime.now() + timedelta(hours=12)
        return TokenResponse(token=token)
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/auth/me")
def me(authorization: Optional[str] = Header(None)):
    token = _extract_token(authorization)
    if token not in _tokens or _tokens[token] < datetime.now():
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"username": TECH_USERNAME}


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    return parts[1] if len(parts) == 2 else None


app.include_router(patients.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "hematology-lab-reports"}



# ===== handler =====

from mangum import Mangum

handler = Mangum(app)