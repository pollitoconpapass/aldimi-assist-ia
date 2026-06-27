import os
import uuid
import asyncpg
from typing import Optional, List
from datetime import datetime
from schemas.db_schemas import (
    User, Document, DNI, MedicalReport, DoctorPatient,
    ChatSession, ChatMessage, Alert, MedicationInventory
)

DELETE_0 = "DELETE 0" # -> constat 2 not trigger the linter :)

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self, dsn: Optional[str] = None):
        dsn = dsn or os.getenv("DATABASE_URL", "")
        self.pool = await asyncpg.create_pool(
            dsn,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()


    # === HELPER FUNCTIONS ===
    async def _fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def _fetch(self, query: str, *args) -> List[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def _execute(self, query: str, *args) -> str:
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)


    # === USERS ===
    async def create_user(self, user: User) -> User:
        row = await self._fetchrow(
            """INSERT INTO users (id, dni, email, password_hash, firstname, lastname,
                                  birthdate, gender, address, phone, role, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
               RETURNING *""",
            user.id, user.dni, user.email, user.password_hash, user.firstname, user.lastname,
            user.birthdate, user.gender, user.address, user.phone, user.role, user.created_at,
        )
        return User(**{k: str(v) if isinstance(v, uuid.UUID) else v for k, v in dict(row).items()})

    async def get_user(self, user_id: str) -> Optional[User]:
        row = await self._fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        return User(**{k: str(v) if isinstance(v, uuid.UUID) else v for k, v in dict(row).items()}) if row else None

    async def get_user_by_dni(self, dni: str) -> Optional[User]:
        row = await self._fetchrow("SELECT * FROM users WHERE dni = $1", dni)
        return User(**{k: str(v) if isinstance(v, uuid.UUID) else v for k, v in dict(row).items()}) if row else None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        row = await self._fetchrow("SELECT * FROM users WHERE email = $1", email)
        return User(**{k: str(v) if isinstance(v, uuid.UUID) else v for k, v in dict(row).items()}) if row else None

    async def update_user(self, user_id: str, **updates) -> Optional[User]:
        allowed = {"email", "password_hash", "firstname", "lastname",
                   "birthdate", "gender", "address", "phone", "role"}
        fields = {k: v for k, v in updates.items() if k in allowed}
        if not fields:
            return await self.get_user(user_id)
        set_clause = ", ".join(f"{k} = ${i + 1}" for i, k in enumerate(fields))
        values = list(fields.values()) + [user_id]
        row = await self._fetchrow(
            f"UPDATE users SET {set_clause} WHERE id = ${len(values)} RETURNING *",
            *values,
        )
        return User(**dict(row)) if row else None

    async def delete_user(self, user_id: str) -> bool:
        result = await self._execute("DELETE FROM users WHERE id = $1", user_id)
        return result != DELETE_0

    async def list_users_by_role(self, role: str) -> List[User]:
        rows = await self._fetch("SELECT * FROM users WHERE role = $1 ORDER BY created_at DESC", role)
        return [User(**dict(r)) for r in rows]
    

    # === DOCUMENTS ===
    async def create_document(self, doc: Document) -> Document:
        row = await self._fetchrow(
            """INSERT INTO documents (id, user_id, type, file_path, ocr_text, uploaded_at)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
            doc.id, doc.user_id, doc.type, doc.file_path, doc.ocr_text, doc.uploaded_at,
        )
        return Document(**dict(row))

    async def get_document(self, doc_id: str) -> Optional[Document]:
        row = await self._fetchrow("SELECT * FROM documents WHERE id = $1", doc_id)
        return Document(**dict(row)) if row else None

    async def get_documents_by_user(self, user_id: str) -> List[Document]:
        rows = await self._fetch(
            "SELECT * FROM documents WHERE user_id = $1 ORDER BY uploaded_at DESC", user_id,
        )
        return [Document(**dict(r)) for r in rows]

    async def get_documents_by_type(self, user_id: str, doc_type: str) -> List[Document]:
        rows = await self._fetch(
            "SELECT * FROM documents WHERE user_id = $1 AND type = $2 ORDER BY uploaded_at DESC",
            user_id, doc_type,
        )
        return [Document(**dict(r)) for r in rows]

    async def update_document_ocr(self, doc_id: str, ocr_text: str) -> Optional[Document]:
        row = await self._fetchrow(
            "UPDATE documents SET ocr_text = $1 WHERE id = $2 RETURNING *", ocr_text, doc_id,
        )
        return Document(**dict(row)) if row else None

    async def delete_document(self, doc_id: str) -> bool:
        result = await self._execute("DELETE FROM documents WHERE id = $1", doc_id)
        return result != DELETE_0


    # === DNI ===
    async def create_dni(self, dni: DNI) -> DNI:
        row = await self._fetchrow(
            """INSERT INTO dni_documents (id, document_id, names, paternal_lastname,
                                          maternal_lastname, date_of_birth, gender)
               VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *""",
            dni.id, dni.document_id, dni.names, dni.paternal_lastname,
            dni.maternal_lastname, dni.date_of_birth, dni.gender,
        )
        return DNI(**dict(row))

    async def get_dni(self, dni_id: str) -> Optional[DNI]:
        row = await self._fetchrow("SELECT * FROM dni_documents WHERE id = $1", dni_id)
        return DNI(**dict(row)) if row else None

    async def get_dni_by_document(self, doc_id: str) -> Optional[DNI]:
        row = await self._fetchrow("SELECT * FROM dni_documents WHERE document_id = $1", doc_id)
        return DNI(**dict(row)) if row else None

    async def get_dni_by_user(self, user_id: str) -> Optional[DNI]:
        row = await self._fetchrow(
            """SELECT d.* FROM dni_documents d
               JOIN documents doc ON doc.id = d.document_id
               WHERE doc.user_id = $1
               ORDER BY doc.uploaded_at DESC LIMIT 1""",
            user_id,
        )
        return DNI(**dict(row)) if row else None


    # === MEDICAL REPORTS ===
    async def create_medical_report(self, report: MedicalReport) -> MedicalReport:
        medications_json = report.medications if report.medications else []
        row = await self._fetchrow(
            """INSERT INTO medical_reports (id, document_id, report_date, condition,
                                            results, medications)
               VALUES ($1, $2, $3, $4, $5, $6::jsonb) RETURNING *""",
            report.id, report.document_id, report.report_date, report.condition,
            report.results, medications_json,
        )
        return MedicalReport(**dict(row))

    async def get_medical_report(self, report_id: str) -> Optional[MedicalReport]:
        row = await self._fetchrow("SELECT * FROM medical_reports WHERE id = $1", report_id)
        return MedicalReport(**dict(row)) if row else None

    async def get_medical_report_by_document(self, doc_id: str) -> Optional[MedicalReport]:
        row = await self._fetchrow("SELECT * FROM medical_reports WHERE document_id = $1", doc_id)
        return MedicalReport(**dict(row)) if row else None

    async def get_reports_by_user(self, user_id: str) -> List[MedicalReport]:
        rows = await self._fetch(
            """SELECT mr.* FROM medical_reports mr
               JOIN documents doc ON doc.id = mr.document_id
               WHERE doc.user_id = $1
               ORDER BY mr.report_date DESC""",
            user_id,
        )
        return [MedicalReport(**dict(r)) for r in rows]


    # === DOCTOR — PATIENT RELATIONSHIP ===
    async def assign_patient(self, doctor_id: str, patient_id: str) -> DoctorPatient:
        row = await self._fetchrow(
            "INSERT INTO doctor_patient (doctor_id, patient_id) VALUES ($1, $2) RETURNING *",
            doctor_id, patient_id,
        )
        return DoctorPatient(**dict(row))

    async def remove_patient(self, doctor_id: str, patient_id: str) -> bool:
        result = await self._execute(
            "DELETE FROM doctor_patient WHERE doctor_id = $1 AND patient_id = $2",
            doctor_id, patient_id,
        )
        return result != DELETE_0

    async def get_doctor_patients(self, doctor_id: str) -> List[User]:
        rows = await self._fetch(
            """SELECT u.* FROM users u
               JOIN doctor_patient dp ON dp.patient_id = u.id
               WHERE dp.doctor_id = $1 ORDER BY u.lastname, u.firstname""",
            doctor_id,
        )
        return [User(**dict(r)) for r in rows]

    async def get_patient_doctors(self, patient_id: str) -> List[User]:
        rows = await self._fetch(
            """SELECT u.* FROM users u
               JOIN doctor_patient dp ON dp.doctor_id = u.id
               WHERE dp.patient_id = $1 ORDER BY u.lastname, u.firstname""",
            patient_id,
        )
        return [User(**dict(r)) for r in rows]

    async def is_patient_assigned(self, doctor_id: str, patient_id: str) -> bool:
        row = await self._fetchrow(
            "SELECT 1 FROM doctor_patient WHERE doctor_id = $1 AND patient_id = $2",
            doctor_id, patient_id,
        )
        return row is not None


    # === CHAT SESSIONS ===
    async def create_chat_session(self, session: ChatSession) -> ChatSession:
        row = await self._fetchrow(
            "INSERT INTO chat_sessions (id, user_id, title, created_at) VALUES ($1, $2, $3, $4) RETURNING *",
            session.id, session.user_id, session.title, session.created_at,
        )
        return ChatSession(**dict(row))

    async def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        row = await self._fetchrow("SELECT * FROM chat_sessions WHERE id = $1", session_id)
        return ChatSession(**dict(row)) if row else None

    async def get_chat_sessions_by_user(self, user_id: str) -> List[ChatSession]:
        rows = await self._fetch(
            "SELECT * FROM chat_sessions WHERE user_id = $1 ORDER BY created_at DESC", user_id,
        )
        return [ChatSession(**dict(r)) for r in rows]

    async def delete_chat_session(self, session_id: str) -> bool:
        result = await self._execute("DELETE FROM chat_sessions WHERE id = $1", session_id)
        return result != DELETE_0

    
    # === CHAT MESSAGES ===
    async def create_chat_message(self, message: ChatMessage) -> ChatMessage:
        row = await self._fetchrow(
            """INSERT INTO chat_messages (id, session_id, role, content, created_at)
               VALUES ($1, $2, $3, $4, $5) RETURNING *""",
            message.id, message.session_id, message.role, message.content, message.created_at,
        )
        return ChatMessage(**dict(row))

    async def get_chat_messages(self, session_id: str) -> List[ChatMessage]:
        rows = await self._fetch(
            "SELECT * FROM chat_messages WHERE session_id = $1 ORDER BY created_at ASC", session_id,
        )
        return [ChatMessage(**dict(r)) for r in rows]

    async def get_last_n_messages(self, session_id: str, n: int = 30) -> List[ChatMessage]:
        rows = await self._fetch(
            """SELECT * FROM chat_messages WHERE session_id = $1
               ORDER BY created_at DESC LIMIT $2""",
            session_id, n,
        )
        return [ChatMessage(**dict(r)) for r in reversed(rows)]


    # === ALERTS ===
    async def create_alert(self, alert: Alert) -> Alert:
        row = await self._fetchrow(
            """INSERT INTO alerts (id, user_id, alert_type, patient_id, alert_text,
                                   score_risk, is_read, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *""",
            alert.id, alert.user_id, alert.alert_type, alert.patient_id,
            alert.alert_text, alert.score_risk, alert.is_read, alert.created_at,
        )
        return Alert(**dict(row))

    async def get_alerts_by_user(self, user_id: str) -> List[Alert]:
        rows = await self._fetch(
            "SELECT * FROM alerts WHERE user_id = $1 ORDER BY created_at DESC", user_id,
        )
        return [Alert(**dict(r)) for r in rows]

    async def get_unread_alerts(self, user_id: str) -> List[Alert]:
        rows = await self._fetch(
            "SELECT * FROM alerts WHERE user_id = $1 AND is_read = FALSE ORDER BY created_at DESC",
            user_id,
        )
        return [Alert(**dict(r)) for r in rows]

    async def get_alerts_by_type(self, user_id: str, alert_type: str) -> List[Alert]:
        rows = await self._fetch(
            "SELECT * FROM alerts WHERE user_id = $1 AND alert_type = $2 ORDER BY created_at DESC",
            user_id, alert_type,
        )
        return [Alert(**dict(r)) for r in rows]

    async def mark_alert_read(self, alert_id: str) -> bool:
        result = await self._execute(
            "UPDATE alerts SET is_read = TRUE WHERE id = $1", alert_id,
        )
        return result != "UPDATE 0"

    async def mark_all_alerts_read(self, user_id: str) -> int:
        result = await self._execute(
            "UPDATE alerts SET is_read = TRUE WHERE user_id = $1 AND is_read = FALSE", user_id,
        )
        return int(result.split()[-1])

    async def delete_alert(self, alert_id: str) -> bool:
        result = await self._execute("DELETE FROM alerts WHERE id = $1", alert_id)
        return result != DELETE_0


    # === MEDICATION INVENTORY ===
    async def create_medication(self, med: MedicationInventory) -> MedicationInventory:
        row = await self._fetchrow(
            """INSERT INTO medication_inventory (id, name, quantity, threshold, unit)
               VALUES ($1, $2, $3, $4, $5) RETURNING *""",
            med.id, med.name, med.quantity, med.threshold, med.unit,
        )
        return MedicationInventory(**dict(row))

    async def get_medication(self, med_id: str) -> Optional[MedicationInventory]:
        row = await self._fetchrow("SELECT * FROM medication_inventory WHERE id = $1", med_id)
        return MedicationInventory(**dict(row)) if row else None

    async def get_medication_by_name(self, name: str) -> Optional[MedicationInventory]:
        row = await self._fetchrow("SELECT * FROM medication_inventory WHERE name = $1", name)
        return MedicationInventory(**dict(row)) if row else None

    async def list_medications(self) -> List[MedicationInventory]:
        rows = await self._fetch(
            "SELECT * FROM medication_inventory ORDER BY name ASC",
        )
        return [MedicationInventory(**dict(r)) for r in rows]

    async def get_low_stock_medications(self) -> List[MedicationInventory]:
        rows = await self._fetch(
            "SELECT * FROM medication_inventory WHERE quantity <= threshold ORDER BY quantity ASC",
        )
        return [MedicationInventory(**dict(r)) for r in rows]

    async def update_medication_quantity(self, med_id: str, quantity: int) -> Optional[MedicationInventory]:
        row = await self._fetchrow(
            "UPDATE medication_inventory SET quantity = $1, updated_at = NOW() WHERE id = $2 RETURNING *",
            quantity, med_id,
        )
        return MedicationInventory(**dict(row)) if row else None

    async def update_medication(self, med_id: str, **updates) -> Optional[MedicationInventory]:
        allowed = {"name", "quantity", "threshold", "unit"}
        fields = {k: v for k, v in updates.items() if k in allowed}
        if not fields:
            return await self.get_medication(med_id)
        fields["updated_at"] = datetime.utc.now()
        set_clause = ", ".join(f"{k} = ${i + 1}" for i, k in enumerate(fields))
        values = list(fields.values()) + [med_id]
        row = await self._fetchrow(
            f"UPDATE medication_inventory SET {set_clause} WHERE id = ${len(values)} RETURNING *",
            *values,
        )
        return MedicationInventory(**dict(row)) if row else None

    async def delete_medication(self, med_id: str) -> bool:
        result = await self._execute("DELETE FROM medication_inventory WHERE id = $1", med_id)
        return result != DELETE_0

    async def adjust_stock(self, med_id: str, delta: int) -> Optional[MedicationInventory]:
        row = await self._fetchrow(
            """UPDATE medication_inventory
               SET quantity = GREATEST(0, quantity + $1), updated_at = NOW()
               WHERE id = $2
               RETURNING *""",
            delta, med_id,
        )
        return MedicationInventory(**dict(row)) if row else None
