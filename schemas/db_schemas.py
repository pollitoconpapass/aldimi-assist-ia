import ast
import json
import re

from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Any, Optional, List, Dict


class User(BaseModel):
    id: str # -> UUID
    dni: str # -> id es el dni
    email: str
    password_hash: str
    firstname: str
    lastname: str
    birthdate: datetime
    gender: str
    address: str
    phone: Optional[str] = None
    role: str  # 'patient' | 'doctor'
    created_at: datetime


class Document(BaseModel):
    id: Any
    user_id: Any
    type: str  # 'dni' | 'medical_report'
    file_path: str
    ocr_text: Optional[str] = None
    uploaded_at: datetime

    @field_validator('id', 'user_id', mode='before')
    @classmethod
    def convert_to_str(cls, v):
        return str(v) if v is not None else v


class DNI(BaseModel):
    id: str
    document_id: str
    names: str
    paternal_lastname: str
    maternal_lastname: str
    date_of_birth: datetime
    gender: str


class MedicalReport(BaseModel):
    id: Any
    document_id: Any
    report_date: str
    condition: str
    results: Optional[str] = None
    medications: Optional[List[Dict]] = None

    @field_validator('id', 'document_id', mode='before')
    @classmethod
    def convert_to_str(cls, v):
        return str(v) if v is not None else v

    @field_validator('report_date', mode='before')
    @classmethod
    def convert_date_to_str(cls, v):
        if hasattr(v, 'isoformat'):
            return v.isoformat()
        return str(v) if v is not None else v

    @field_validator('medications', mode='before')
    @classmethod
    def parse_medications(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
            try:
                return ast.literal_eval(v)
            except (ValueError, SyntaxError):
                pass
            quoted = re.sub(r'([{,]\s*)(\w+)\s*:', r'\1"\2":', v)
            try:
                return json.loads(quoted)
            except json.JSONDecodeError:
                return v
        return v


class DoctorPatient(BaseModel):
    doctor_id: str
    patient_id: str
    assigned_at: datetime


class ChatSession(BaseModel):
    id: Any
    user_id: Any
    title: Optional[str] = None
    created_at: datetime

    @field_validator('id', 'user_id', mode='before')
    @classmethod
    def convert_to_str(cls, v):
        return str(v) if v is not None else v


class ChatMessage(BaseModel):
    id: Any
    session_id: Any
    role: str  # 'user' | 'ai'
    content: str
    created_at: datetime

    @field_validator('id', 'session_id', mode='before')
    @classmethod
    def convert_to_str(cls, v):
        return str(v) if v is not None else v


class Alert(BaseModel):
    id: str
    user_id: str
    alert_type: str  # 'critical_health' | 'mental_health' | 'medication_stock'
    patient_id: Optional[str] = None
    alert_text: str
    score_risk: float
    is_read: bool = False
    created_at: datetime


class MedicationInventory(BaseModel):
    id: str
    name: str
    quantity: int
    threshold: int
    unit: str


class DocumentChunk(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    created_at: datetime
