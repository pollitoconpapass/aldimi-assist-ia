from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict


class User(BaseModel):
    id: str # -> id es el dni
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
    id: str
    user_id: str
    type: str  # 'dni' | 'medical_report'
    file_path: str
    ocr_text: Optional[str] = None
    uploaded_at: datetime


class DNI(BaseModel):
    id: str
    document_id: str
    names: str
    paternal_lastname: str
    maternal_lastname: str
    date_of_birth: datetime
    gender: str


class MedicalReport(BaseModel):
    id: str
    document_id: str
    report_date: datetime
    condition: str
    results: Optional[str] = None
    medications: Optional[List[Dict]] = None


class DoctorPatient(BaseModel):
    doctor_id: str
    patient_id: str
    assigned_at: datetime


class ChatSession(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    created_at: datetime


class ChatMessage(BaseModel):
    id: str
    session_id: str
    role: str  # 'user' | 'ai'
    content: str
    created_at: datetime


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
