import asyncpg
from typing import Optional
import pgvector.asyncpg as pgvector
from helpers.vect_db_helpers import chunk_text
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        if self._model is None:
            self._model = SentenceTransformer(
                model_name,
                model_kwargs={"trust_remote_code": True},
            )
        return self._model

    def encode(self, text: str) -> list[float]:
        model = self.load()
        return model.encode(text, normalize_embeddings=True).tolist()

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        model = self.load()
        return model.encode(texts, normalize_embeddings=True).tolist()



class VectorDB:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.embedder = EmbeddingModel()

    async def index_document(self, document_id: str, ocr_text: str) -> int:
        chunks = chunk_text(ocr_text)
        if not chunks:
            return 0

        embeddings = self.embedder.encode_batch(chunks)

        async with self.pool.acquire() as conn:
            await pgvector.register_vector(conn)
            for i, (text, emb) in enumerate(zip(chunks, embeddings)):
                await conn.execute(
                    """INSERT INTO document_chunks (document_id, chunk_index, chunk_text, embedding)
                       VALUES ($1, $2, $3, $4::vector)
                       ON CONFLICT (document_id, chunk_index)
                       DO UPDATE SET chunk_text = $3, embedding = $4::vector""",
                    document_id, i, text, emb,
                )

        return len(chunks)

    async def delete_document_chunks(self, document_id: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM document_chunks WHERE document_id = $1",
                document_id,
            )

    async def reindex_document(self, document_id: str, ocr_text: str) -> int:
        await self.delete_document_chunks(document_id)
        return await self.index_document(document_id, ocr_text)

    # When a user searches own documents
    async def search(self, query: str, user_id: str, top_k: int = 5, min_score: float = 0.2) -> list[dict]:
        query_emb = self.embedder.encode(query)

        async with self.pool.acquire() as conn:
            await pgvector.register_vector(conn)
            rows = await conn.fetch(
                """SELECT dc.chunk_text, dc.chunk_index, dc.document_id,
                          doc.type AS document_type,
                          1 - (dc.embedding <=> $1::vector) AS score
                   FROM document_chunks dc
                   JOIN documents doc ON doc.id = dc.document_id
                   WHERE doc.user_id = $2
                     AND 1 - (dc.embedding <=> $1::vector) >= $3
                   ORDER BY score DESC
                   LIMIT $4""",
                query_emb, user_id, min_score, top_k,
            )

        return [
            {
                "chunk_text": r["chunk_text"],
                "chunk_index": r["chunk_index"],
                "document_id": r["document_id"],
                "document_type": r["document_type"],
                "score": r["score"],
            }
            for r in rows
        ]

    # When a doctor searches documents of all their patients. (query example: "¿Cuáles de mis pacientes han tenido resultados anormales en sus análisis de sangre?")
    async def search_by_doctor(self, query: str, doctor_id: str, top_k: int = 5, min_score: float = 0.5,) -> list[dict]:
        query_emb = self.embedder.encode(query)

        async with self.pool.acquire() as conn:
            await pgvector.register_vector(conn)
            rows = await conn.fetch(
                """SELECT dc.chunk_text, dc.chunk_index, dc.document_id,
                          doc.type AS document_type, doc.user_id AS patient_id,
                          1 - (dc.embedding <=> $1::vector) AS score
                   FROM document_chunks dc
                   JOIN documents doc ON doc.id = dc.document_id
                   JOIN doctor_patient dp ON dp.patient_id = doc.user_id
                   WHERE dp.doctor_id = $2
                     AND 1 - (dc.embedding <=> $1::vector) >= $3
                   ORDER BY score DESC
                   LIMIT $4""",
                query_emb, doctor_id, min_score, top_k,
            )

        return [
            {
                "chunk_text": r["chunk_text"],
                "chunk_index": r["chunk_index"],
                "document_id": r["document_id"],
                "document_type": r["document_type"],
                "patient_id": r["patient_id"],
                "score": r["score"],
            }
            for r in rows
        ]

    # When we want to search for only one specific patient (query example: "¿Qué condicion tiene el paciente Juan Pérez?")
    async def search_by_patient(self, query: str, patient_id: str, doctor_id: Optional[str] = None, top_k: int = 5, min_score: float = 0.5) -> list[dict]:
        query_emb = self.embedder.encode(query)

        async with self.pool.acquire() as conn:
            await pgvector.register_vector(conn)

            if doctor_id:
                rows = await conn.fetch(
                    """SELECT dc.chunk_text, dc.chunk_index, dc.document_id,
                              doc.type AS document_type, doc.user_id AS patient_id,
                              1 - (dc.embedding <=> $1::vector) AS score
                       FROM document_chunks dc
                       JOIN documents doc ON doc.id = dc.document_id
                       JOIN doctor_patient dp ON dp.patient_id = doc.user_id
                       WHERE doc.user_id = $2
                         AND dp.doctor_id = $3
                         AND 1 - (dc.embedding <=> $1::vector) >= $4
                       ORDER BY score DESC
                       LIMIT $5""",
                    query_emb, patient_id, doctor_id, min_score, top_k,
                )
            else:
                rows = await conn.fetch(
                    """SELECT dc.chunk_text, dc.chunk_index, dc.document_id,
                              doc.type AS document_type, doc.user_id AS patient_id,
                              1 - (dc.embedding <=> $1::vector) AS score
                       FROM document_chunks dc
                       JOIN documents doc ON doc.id = dc.document_id
                       WHERE doc.user_id = $2
                         AND 1 - (dc.embedding <=> $1::vector) >= $3
                       ORDER BY score DESC
                       LIMIT $4""",
                    query_emb, patient_id, min_score, top_k,
                )

        return [
            {
                "chunk_text": r["chunk_text"],
                "chunk_index": r["chunk_index"],
                "document_id": r["document_id"],
                "document_type": r["document_type"],
                "patient_id": r["patient_id"],
                "score": r["score"],
            }
            for r in rows
        ]
