"""Hematology Lab Reports API — single-file Vercel deployment."""
import io
import os
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, func, extract
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ── Database ──────────────────────────────────────────────────────
_DB_DIR = "/tmp"
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(_DB_DIR, 'labreports.db')}"
)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ── Models ────────────────────────────────────────────────────────
class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    gender = Column(String, nullable=False)
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
    verification_status = Column(String, nullable=True, default="auto_verified")
    verification_notes = Column(Text, nullable=True)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    patient = relationship("Patient", back_populates="reports")
    results = relationship("Result", back_populates="report", cascade="all, delete-orphan")


class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    parameter_name = Column(String, nullable=False)
    result_value = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    ref_range_low = Column(Float, nullable=True)
    ref_range_high = Column(Float, nullable=True)
    flag = Column(String, nullable=True)
    report = relationship("Report", back_populates="results")


Base.metadata.create_all(bind=engine)

# ── Schemas ───────────────────────────────────────────────────────
class PatientCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    gender: str
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
    status: str
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

# ── References ────────────────────────────────────────────────────
PANEL_TYPE_LMG = "LMG"
PANEL_TYPE_NEU = "NEU"

PARAMETERS = [
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
    ("rbc", "RBC (Red Blood Cell Count)", "M/uL", "rbc"),
    ("hgb", "HGB (Haemoglobin)", "g/dL", "rbc"),
    ("hct", "HCT (Haematocrit)", "%", "rbc"),
    ("mcv", "MCV (Mean Corpuscular Volume)", "fL", "rbc"),
    ("mch", "MCH (Mean Corpuscular Hb)", "pg", "rbc"),
    ("mchc", "MCHC (Mean Corpuscular Hb Conc.)", "g/dL", "rbc"),
    ("rdw_cv", "RDW-CV", "%", "rbc"),
    ("rdw_sd", "RDW-SD", "fL", "rbc"),
    ("plt", "PLT (Platelet Count)", "x10^3/uL", "plt"),
    ("mpv", "MPV (Mean Platelet Volume)", "fL", "plt"),
    ("pdw", "PDW (Platelet Distribution Width)", "%", "plt"),
    ("pct", "PCT (Platelet Crit)", "%", "plt"),
]
PARAM_BY_KEY = {k: (label, unit, group) for k, label, unit, group in PARAMETERS}

ADULT_REFS = {
    "male": {
        "wbc": (4.0, 11.0), "lymph_pct": (20.0, 45.0), "mid_pct": (3.0, 12.0),
        "gran_pct": (45.0, 70.0), "lymph_abs": (1000.0, 4800.0), "mid_abs": (200.0, 1200.0),
        "gran_abs": (2500.0, 7000.0), "neu_pct": (40.0, 75.0), "mono_pct": (2.0, 10.0),
        "eoso_pct": (1.0, 6.0), "baso_pct": (0.0, 2.0), "rbc": (4.5, 5.9),
        "hgb": (13.5, 18.0), "hct": (40.0, 54.0), "mcv": (80.0, 100.0),
        "mch": (27.0, 33.0), "mchc": (32.0, 36.0), "rdw_cv": (11.5, 14.5),
        "rdw_sd": (37.0, 54.0), "plt": (150.0, 450.0), "mpv": (7.4, 10.4),
        "pdw": (9.0, 17.0), "pct": (0.15, 0.40),
    },
    "female": {
        "wbc": (4.0, 11.0), "lymph_pct": (20.0, 45.0), "mid_pct": (3.0, 12.0),
        "gran_pct": (45.0, 70.0), "lymph_abs": (1000.0, 4800.0), "mid_abs": (200.0, 1200.0),
        "gran_abs": (2500.0, 7000.0), "neu_pct": (40.0, 75.0), "mono_pct": (2.0, 10.0),
        "eoso_pct": (1.0, 6.0), "baso_pct": (0.0, 2.0), "rbc": (4.0, 5.2),
        "hgb": (12.0, 16.0), "hct": (36.0, 48.0), "mcv": (80.0, 100.0),
        "mch": (27.0, 33.0), "mchc": (32.0, 36.0), "rdw_cv": (11.5, 14.5),
        "rdw_sd": (37.0, 54.0), "plt": (150.0, 450.0), "mpv": (7.4, 10.4),
        "pdw": (9.0, 17.0), "pct": (0.15, 0.40),
    },
}
PEDIATRIC_REFS = {
    "wbc": (5.0, 13.0), "rbc": (3.9, 5.5), "hgb": (11.0, 15.0),
    "hct": (33.0, 44.0), "mcv": (78.0, 98.0), "mch": (25.0, 33.0),
    "mchc": (31.0, 36.0), "plt": (150.0, 450.0), "mpv": (7.4, 10.4),
    "pdw": (9.0, 17.0), "pct": (0.15, 0.40),
}

def default_ref_for(key, age, gender):
    if age is not None and age < 14 and key in PEDIATRIC_REFS:
        return PEDIATRIC_REFS[key]
    gkey = "male" if gender == "Male" else "female"
    return ADULT_REFS.get(gkey, ADULT_REFS["male"]).get(key, (None, None))

def compute_flag(value, low, high):
    if value is None or low is None or high is None:
        return "normal"
    if value > high:
        return "H"
    if value < low:
        return "L"
    return "normal"

# ── Services ──────────────────────────────────────────────────────
def generate_patient_id(session):
    count = session.query(func.count(Patient.id)).scalar() or 0
    base = int(count) + 1
    candidate = f"PT-{base:06d}"
    while session.query(Patient).filter(Patient.patient_id == candidate).first():
        base += 1
        candidate = f"PT-{base:06d}"
    return candidate

def generate_sample_id(session):
    now = datetime.now()
    day_prefix = now.strftime("%Y%m%d")
    count = (
        session.query(func.count(Report.id))
        .filter(extract("year", Report.created_at) == now.year, extract("month", Report.created_at) == now.month, extract("day", Report.created_at) == now.day)
        .scalar() or 0
    )
    seq = int(count) + 1
    candidate = f"S-{day_prefix}-{seq:03d}"
    while session.query(Report).filter(Report.sample_id == candidate).first():
        seq += 1
        candidate = f"S-{day_prefix}-{seq:03d}"
    return candidate

def compute_verification_status(results, current_status="auto_verified"):
    has_abnormal = any((r.flag or "normal") in ("H", "L") for r in results)
    if current_status in ("reviewed", "revised"):
        return current_status
    return "pending_review" if has_abnormal else "auto_verified"

# ── App ───────────────────────────────────────────────────────────
class StripApiPrefixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/api/"):
            request.scope["path"] = request.url.path[4:]  # strip "/api"
            if request.scope.get("root_path", "").startswith("/api"):
                request.scope["root_path"] = request.scope["root_path"][4:]
        return await call_next(request)

app = FastAPI(title="Hematology Lab Reports API")
app.add_middleware(StripApiPrefixMiddleware)

TECH_USERNAME = "technician"
TECH_PASSWORD = "lab123"
_tokens = {}

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
    if credentials.username == TECH_USERNAME and credentials.password == TECH_PASSWORD:
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

def _extract_token(authorization):
    if not authorization:
        return None
    parts = authorization.split()
    return parts[1] if len(parts) == 2 else None

@app.get("/")
def root():
    return {"status": "ok", "service": "hematology-lab-reports"}

# ── Patients Router ───────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/patients", response_model=PatientOut, status_code=201)
def create_patient(payload: PatientCreate, db=Depends(get_db)):
    patient = Patient(first_name=payload.first_name, last_name=payload.last_name, gender=payload.gender, age=payload.age)
    db.add(patient)
    patient.patient_id = generate_patient_id(db)
    db.commit()
    db.refresh(patient)
    return patient

@app.get("/patients", response_model=list[PatientOut])
def list_patients(db=Depends(get_db)):
    return db.query(Patient).order_by(Patient.created_at.desc()).all()

@app.get("/patients/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db=Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

# ── Reports Router ────────────────────────────────────────────────
def _validate_flag(value):
    if value is None:
        return "normal"
    f = value.strip().upper()
    return f if f in ("H", "L", "NORMAL") else "normal"

def _normalize_key(value):
    return value.strip().lower()

def _load_report(db, report_id):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@app.post("/reports", response_model=ReportOut, status_code=201)
def create_report(payload: ReportCreate, db=Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    report = Report(patient_id=payload.patient_id, requested_by=payload.requested_by, technologist_name=payload.technologist_name, comments=payload.comments, test_date=payload.test_date or datetime.now(), source=payload.source)
    db.add(report)
    report.sample_id = generate_sample_id(db)
    db.flush()
    existing = {r.parameter_name for r in report.results}
    results = []
    for item in payload.results:
        key = _normalize_key(item.parameter_name)
        if key in existing:
            continue
        existing.add(key)
        result = Result(report_id=report.id, parameter_name=key, result_value=item.result_value, unit=item.unit, ref_range_low=item.ref_range_low, ref_range_high=item.ref_range_high, flag=_validate_flag(item.flag))
        if item.flag is None and item.result_value is not None:
            result.flag = compute_flag(item.result_value, item.ref_range_low, item.ref_range_high)
        db.add(result)
        results.append(result)
    report.verification_status = compute_verification_status(results)
    db.commit()
    db.refresh(report)
    return report

@app.get("/reports", response_model=list[ReportOut])
def list_reports(q: str = None, limit: int = 100, db=Depends(get_db)):
    query = db.query(Report).join(Patient)
    if q:
        like = f"%{q}%"
        query = query.filter(Patient.first_name.ilike(like) | Patient.last_name.ilike(like) | Patient.patient_id.ilike(like) | Report.sample_id.ilike(like))
    return query.order_by(Report.created_at.desc()).limit(min(limit, 500)).all()

@app.get("/reports/queue/review", response_model=list[ReportOut])
def review_queue(db=Depends(get_db)):
    return db.query(Report).filter(Report.verification_status == "pending_review").order_by(Report.created_at.asc()).all()

@app.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db=Depends(get_db)):
    return _load_report(db, report_id)

@app.put("/reports/{report_id}", response_model=ReportOut)
def update_report(report_id: int, payload: ReportUpdate, db=Depends(get_db)):
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
            result = Result(report_id=report_id, parameter_name=key, result_value=item.result_value, unit=item.unit, ref_range_low=item.ref_range_low, ref_range_high=item.ref_range_high, flag=_validate_flag(item.flag))
            if item.flag is None and item.result_value is not None:
                result.flag = compute_flag(item.result_value, item.ref_range_low, item.ref_range_high)
            db.add(result)
            updated_results.append(result)
        report.verification_status = compute_verification_status(updated_results, report.verification_status)
    db.commit()
    db.refresh(report)
    return report

@app.delete("/reports/{report_id}", status_code=204)
def delete_report(report_id: int, db=Depends(get_db)):
    report = _load_report(db, report_id)
    db.delete(report)
    db.commit()

@app.post("/reports/{report_id}/verify", response_model=ReportOut)
def verify_report(report_id: int, payload: VerificationUpdate, db=Depends(get_db)):
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

@app.get("/reports/{report_id}/pdf")
def download_pdf(report_id: int, db=Depends(get_db)):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ImportError:
        raise HTTPException(status_code=501, detail="PDF generation not available")
    report = _load_report(db, report_id)
    patient = report.patient
    results = sorted(report.results, key=lambda r: _pdf_param_index(r.parameter_name))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=16, alignment=1, textColor=colors.HexColor("#1e3a8a"), spaceAfter=2)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], alignment=1, fontSize=10, textColor=colors.grey)
    h_style = ParagraphStyle("Hdr", parent=styles["Normal"], fontSize=9, leading=12)
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9)
    story = []
    story.append(Paragraph("HAEMATOLOGY LABORATORY", title_style))
    story.append(Paragraph("Fully Automated Haematology Analyzer Report", sub_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("123 Lab Street - Tel: +0 000 0000", sub_style))
    story.append(Spacer(1, 8))
    info_data = [
        [Paragraph(f"<b>Patient ID:</b> {patient.patient_id}", h_style), Paragraph(f"<b>Sample ID:</b> {report.sample_id}", h_style)],
        [Paragraph(f"<b>Name:</b> {patient.first_name} {patient.last_name}", h_style), Paragraph(f"<b>Age:</b> {patient.age}", h_style)],
        [Paragraph(f"<b>Gender:</b> {patient.gender}", h_style), Paragraph(f"<b>Requested By:</b> {report.requested_by or '-'}", h_style)],
        [Paragraph(f"<b>Test Date:</b> {report.test_date or report.created_at}", h_style), Paragraph(f"<b>Technologist:</b> {report.technologist_name or '-'}", h_style)],
    ]
    info_table = Table(info_data, colWidths=[doc.width/2, doc.width/2])
    info_table.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")), ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f8fafc")), ("LEFTPADDING", (0,0), (-1,-1), 6), ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4)]))
    story.append(info_table)
    story.append(Spacer(1, 10))
    header = [Paragraph("<b>Parameter</b>", cell_style), Paragraph("<b>Result</b>", cell_style), Paragraph("<b>Unit</b>", cell_style), Paragraph("<b>Reference Range</b>", cell_style), Paragraph("<b>Flag</b>", cell_style)]
    body = [header]
    highlight = []
    for r in results:
        flag = (r.flag or "normal").upper()
        flag_color = "red" if flag == "H" else "blue" if flag == "L" else "green"
        label = PARAM_BY_KEY.get(r.parameter_name, (r.parameter_name, "", ""))[0]
        ref = f"{r.ref_range_low or '-'} - {r.ref_range_high or '-'}" if r.ref_range_low is not None or r.ref_range_high is not None else ""
        row = [Paragraph(label, cell_style), Paragraph(f"{r.result_value if r.result_value is not None else '-'}", cell_style), Paragraph(f"{r.unit or '-'}", cell_style), Paragraph(ref, cell_style), Paragraph(f'<font color="{flag_color}">{"" if flag == "NORMAL" else flag}</font>', cell_style)]
        body.append(row)
        if flag in ("H", "L"):
            highlight.append(len(body) - 1)
    res_table = Table(body, colWidths=[doc.width*0.42, doc.width*0.14, doc.width*0.14, doc.width*0.2, doc.width*0.1])
    style_cmds = [("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")), ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1e3a8a")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("LEFTPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3)]
    for row_idx in highlight:
        style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#fef2f2")))
    res_table.setStyle(TableStyle(style_cmds))
    story.append(res_table)
    story.append(Spacer(1, 6))
    if report.comments:
        story.append(Paragraph(f"<b>Comments:</b> {report.comments}", h_style))
        story.append(Spacer(1, 10))
    story.append(Spacer(1, 16))
    story.append(Paragraph(f"______________________________<br/><b>Technologist Signature</b>&nbsp;&nbsp;{report.technologist_name or ''}", h_style))
    doc.build(story)
    buf.seek(0)
    filename = f"report_{report.sample_id}.pdf"
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

def _pdf_param_index(key):
    order = {k: i for i, (k, *_) in enumerate(PARAMETERS)}
    return order.get(key, 999)

# ── Vercel handler ────────────────────────────────────────────────
# Vercel Python runtime handles ASGI directly — no Mangum needed.
