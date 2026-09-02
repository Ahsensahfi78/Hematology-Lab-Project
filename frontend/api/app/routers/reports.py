import io
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Patient, Report, Result
from ..references import compute_flag, PARAM_DESCRIPTIONS, PARAM_BY_KEY, PARAMETERS
from ..schemas import ReportCreate, ReportOut, ReportUpdate, VerificationUpdate
from ..services import generate_sample_id, compute_verification_status

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
