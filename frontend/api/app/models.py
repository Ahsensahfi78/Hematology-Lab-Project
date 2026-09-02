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
