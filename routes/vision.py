import os
import uuid
import asyncio
import re
from datetime import datetime
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from modules.chat.llm import LLM
from modules.data.sql_db import Database
from modules.data.vect_db import VectorDB
from modules.vision.vision import OCRModule
from modules.vision.detect_document_type import predict_document_type
from schemas.db_schemas import DNI, Document, MedicalReport
from schemas.api_schemas import DocumentTypeRequest, SaveDocumentRequest, FormatTextRequest

router = APIRouter(prefix="/vision", tags=["vision"])

@router.post("/ocr")
async def ocr(file: UploadFile = File(...), mode: str = Form(...)):
    ocr = OCRModule(mode)
    text = await ocr.analyze_image_default(file)
    print(f"=== OCR Result: {text} ===")
    return text
    

@router.post("/detect-type")
async def detect_type(request: DocumentTypeRequest):
    document_type = predict_document_type(request.text)
    return document_type


@router.post("/format-text")
async def format_text(request: FormatTextRequest):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY no configurada")

    llm = LLM(api_key=api_key)

    if request.document_type == "dni":
        result = await asyncio.to_thread(
            llm.extract_structured,
            text=request.ocr_text,
            schema=DNI,
            prompt="Extrae los datos del DNI peruano desde el texto OCR. "
                   "Debes extraer: dni (número de DNI, como string), names (nombres), paternal_lastname (apellido paterno), "
                   "maternal_lastname (apellido materno), date_of_birth (fecha de nacimiento en ISO 8601) y gender (género)."
        )

    elif request.document_type == "medical_report":
        result = await asyncio.to_thread(
            llm.extract_structured,
            text=request.ocr_text,
            schema=MedicalReport,
            prompt="Extrae los datos del reporte médico desde el texto OCR. "
                   "Debes extraer: report_date (fecha del reporte en formato YYYY-MM-DD), "
                   "condition (diagnóstico o condición médica), "
                   "results (resultados de exámenes, opcional) y "
                   "medications (lista de medicamentos con nombre y dosis, opcional)."
        )

    else:
        raise HTTPException(status_code=400, detail=f"Tipo de documento inválido: {request.document_type}")

    return result

        
@router.post("/save")
async def save_document(request: SaveDocumentRequest):
    db = Database()
    await db.connect()

    doc_id = str(uuid.uuid4())

    if request.document_type not in ("dni", "medical_report"):
        raise HTTPException(status_code=400, detail=f"Tipo de documento inválido: {request.document_type}")

    user_id = request.user_id
    is_uuid = re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', user_id)
    if not is_uuid:
        user = await db.get_user_by_dni(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"No se encontró usuario con id o DNI: {user_id}")
        user_id = user.id

    document = Document(
        id=doc_id,
        user_id=user_id,
        type=request.document_type,
        file_path=request.file_path,
        ocr_text=request.ocr_text,
        uploaded_at=datetime.now()
    )

    await db.create_document(document)

    if request.document_type == "dni":
        if not request.dni_data:
            raise HTTPException(status_code=400, detail="dni_data es requerido para documentos DNI")

        dni_record = DNI(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            names=request.dni_data.get("names"),
            paternal_lastname=request.dni_data.get("paternal_lastname"),
            maternal_lastname=request.dni_data.get("maternal_lastname"),
            date_of_birth=request.dni_data.get("date_of_birth"),
            gender=request.dni_data.get("gender")
        )
        await db.create_dni(dni_record)
        result = {"document": document, "dni": dni_record}

    elif request.document_type == "medical_report":
        if not request.medical_report_data:
            raise HTTPException(status_code=400, detail="medical_report_data es requerido para reportes médicos")

        report_record = MedicalReport(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            report_date=request.medical_report_data.get("report_date"),
            condition=request.medical_report_data.get("condition"),
            results=request.medical_report_data.get("results"),
            medications=request.medical_report_data.get("medications")
        )
        await db.create_medical_report(report_record)
        result = {"document": document, "medical_report": report_record}

        # We need to know who is the user in the medical report
        user = await db.get_user(user_id)
        patient_name = f"{user.firstname} {user.lastname}" if user else "Unknown Patient"

        # Vector DB indexing
        vector_db = VectorDB(db.pool)
        text_to_index = f'''Paciente: {patient_name}  (id: {user_id})  
            Fecha del reporte: {report_record.report_date}
            Condición: {report_record.condition}
            Resultados: {report_record.results or "N/A"}
            Medicamentos: {"; ".join([f"{med.get('name', '')} ({med.get('dosage', '')})" for med in report_record.medications or []]) or "N/A"}

        '''
        await vector_db.index_document(doc_id, text_to_index)

    return result
