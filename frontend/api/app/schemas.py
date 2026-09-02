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
