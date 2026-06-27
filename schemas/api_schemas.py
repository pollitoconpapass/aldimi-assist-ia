from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from fastapi import UploadFile, File


class SignupRequest(BaseModel):
    dni: str
    email: str
    password: str
    firstname: str
    lastname: str
    birthdate: datetime
    gender: str
    address: str
    phone: Optional[str] = None
    role: str  # 'patient' | 'doctor'

class LogInRequest(BaseModel):
    email: str
    password: str


class OCRRequest(BaseModel):
    file: UploadFile = File(...)
    mode: str # -> default | custom


class DocumentTypeRequest(BaseModel):
    text: str

class FormatTextRequest(BaseModel):
    ocr_text: str
    document_type: str

class SaveDocumentRequest(BaseModel):
    user_id: str
    document_type: str  # 'dni' | 'medical_report'
    file_path: str
    ocr_text: str
    dni_data: Optional[dict] = None
    medical_report_data: Optional[dict] = None


class CreateSessionRequest(BaseModel):
    user_id: str
    title: Optional[str] = None


class SendMessageRequest(BaseModel):
    session_id: str
    user_id: str
    content: str


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime


class ChatSessionResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    created_at: datetime
    message_count: int = 0

class ChatIntention(BaseModel):
    normal_conversation: bool = False
    patient_information: bool = False
    administrative_question: bool = False