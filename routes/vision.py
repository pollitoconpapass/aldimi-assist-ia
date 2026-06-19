import os
import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException

from modules.chat.llm import LLM
from modules.data.sql_db import Database
from modules.data.vect_db import VectorDB
from modules.vision.detect_document_type import predict_document_type
from modules.vision.vision import OCRModule
from schemas.api_schemas import DocumentTypeRequest, OCRRequest, SaveDocumentRequest
from schemas.db_schemas import DNI, Document, MedicalReport

router = APIRouter(prefix="/vision", tags=["vision"])

@router.post("/ocr")
async def ocr(request: OCRRequest):
    ocr = OCRModule(request.mode)
    filename = request.file.filename
    text = ocr.analyze_image_default(filename)
    return text
    

@router.post("/detect-type")
async def detect_type(request: DocumentTypeRequest):
    document_type = predict_document_type(request.text)
    return document_type


@router.post("/save")
async def save_document(request: SaveDocumentRequest):
    db = Database()
    await db.connect()

    doc_id = str(uuid.uuid4())

    if request.document_type not in ("dni", "medical_report"):
        raise HTTPException(status_code=400, detail=f"Tipo de documento inválido: {request.document_type}")

    document = Document(
        id=doc_id,
        user_id=request.user_id,
        type=request.document_type,
        file_path=request.file_path,
        ocr_text=request.ocr_text,
        uploaded_at=datetime.now()
    )

    await db.create_document(document)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY no configurada")

    llm = LLM(api_key=api_key)

    if request.document_type == "dni":
        dni = await asyncio.to_thread(
            llm.extract_structured,
            text=request.ocr_text,
            schema=DNI,
            prompt="Extrae los datos del DNI peruano desde el texto OCR. "
                   "Debes extraer: names (nombres), paternal_lastname (apellido paterno), "
                   "maternal_lastname (apellido materno), date_of_birth (fecha de nacimiento en ISO 8601) y gender (género)."
        )

        dni_record = DNI(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            names=dni.names,
            paternal_lastname=dni.paternal_lastname,
            maternal_lastname=dni.maternal_lastname,
            date_of_birth=dni.date_of_birth,
            gender=dni.gender
        )
        await db.create_dni(dni_record)
        result = {"document": document, "dni": dni_record}

    elif request.document_type == "medical_report":
        report = await asyncio.to_thread(
            llm.extract_structured,
            text=request.ocr_text,
            schema=MedicalReport,
            prompt="Extrae los datos del reporte médico desde el texto OCR. "
                   "Debes extraer: report_date (fecha del reporte en ISO 8601), "
                   "condition (diagnóstico o condición médica), "
                   "results (resultados de exámenes, opcional) y "
                   "medications (lista de medicamentos con nombre y dosis, opcional)."
        )

        report_record = MedicalReport(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            report_date=report.report_date,
            condition=report.condition,
            results=report.results,
            medications=report.medications
        )
        await db.create_medical_report(report_record)
        result = {"document": document, "medical_report": report_record}

    # Vector DB indexing
    vector_db = VectorDB()
    await vector_db.index_document(doc_id, request.ocr_text)

    return result
