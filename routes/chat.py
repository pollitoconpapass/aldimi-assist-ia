import os
import uuid
import aiofiles
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException
from modules.data.sql_db import Database
from modules.chat.llm import LLM
from modules.chat.detect_chat_intention import final_chat_intention_predictor
from modules.data.vect_db import VectorDB
from helpers.vect_db_helpers import format_chunks_as_context
from schemas.db_schemas import ChatSession, ChatMessage
from schemas.api_schemas import (
    CreateSessionRequest,
    SendMessageRequest,
    ChatMessageResponse,
    ChatSessionResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])

SESSION_NOT_FOUND_MESSAGE = "Session not found"
NOT_AUTHORIZED_MESSAGE = "Not authorized for this session"
MAIN_PROMPT_FILE_NAME = "main_prompt.txt"


def _get_llm() -> LLM:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
    return LLM(api_key=api_key)


@router.get("/sessions/{user_id}", response_model=list[ChatSessionResponse]) # -> get all chat sessions
async def get_sessions(user_id: str):
    db = Database()
    await db.connect()
    sessions = await db.get_chat_sessions_by_user(user_id)

    result = []
    for s in sessions:
        messages = await db.get_chat_messages(s.id)
        result.append(ChatSessionResponse(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            created_at=s.created_at,
            message_count=len(messages),
        ))
    return result


@router.post("/sessions", response_model=ChatSessionResponse) # -> create new chat session
async def create_session(request: CreateSessionRequest):
    db = Database()
    await db.connect()

    session = ChatSession(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        title=request.title,
        created_at=datetime.now(),
    )
    created = await db.create_chat_session(session)
    return ChatSessionResponse(
        id=created.id,
        user_id=created.user_id,
        title=created.title,
        created_at=created.created_at,
        message_count=0,
    )


@router.get("/sessions/detail/{session_id}", response_model=ChatSessionResponse) # -> Get single chat session details
async def get_session(session_id: str):
    db = Database()
    await db.connect()
    session = await db.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MESSAGE)

    messages = await db.get_chat_messages(session.id)
    return ChatSessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        created_at=session.created_at,
        message_count=len(messages),
    )


@router.delete("/sessions/{session_id}") # -> Delete session
async def delete_session(session_id: str):
    db = Database()
    await db.connect()
    deleted = await db.delete_chat_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MESSAGE)
    return {"deleted": True}


@router.get("/messages/{session_id}", response_model=list[ChatMessageResponse]) # -> Get all messages from a session
async def get_messages(session_id: str):
    db = Database()
    await db.connect()
    session = await db.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MESSAGE)

    messages = await db.get_chat_messages(session_id)
    return [
        ChatMessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]


# === SEND MESSAGES ENDPOINTS ===
@router.post("/messages", response_model=ChatMessageResponse) # -> Send message (patients)
async def send_message(request: SendMessageRequest):
    db = Database()
    await db.connect()

    session = await db.get_chat_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MESSAGE)
    if session.user_id != request.user_id:
        raise HTTPException(status_code=403, detail=NOT_AUTHORIZED_MESSAGE)

    user_message = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=request.session_id,
        role="user",
        content=request.content,
        created_at=datetime.now(),
    )
    await db.create_chat_message(user_message)

    history = await db.get_last_n_messages(request.session_id, n=30)
    history_text = "\n".join(f"{m.role}: {m.content}" for m in history)

    # init LLM y prompt directory
    llm = _get_llm()
    prompts_dir = Path(__file__).resolve().parent.parent / "modules" / "chat" / "prompts"

    try:
        async with aiofiles.open(prompts_dir / MAIN_PROMPT_FILE_NAME, "r") as pf:
            main_prompt = await pf.read()
    except Exception:
        main_prompt = None

    # Detect chat intention
    intention = final_chat_intention_predictor(llm, request.content)

    context = None
    if intention == "patient_information": # -> Si es una pregunta de informacion del paciente, se le pasa la informacion del paciente
        print("Searching for patient information in the vector database...")
        try:
            vect_db = VectorDB(pool=db.pool)
            context_chunks = await vect_db.search(query=request.content, user_id=request.user_id)
            print(f"Found {len(context_chunks)} context chunks:")
            context = format_chunks_as_context(context_chunks) if context_chunks else None
            print("Context:", context)
        except Exception as e:
            print(f"Vector search error: {e}")
            context = None
    elif intention == "administrative_question": # -> Si es una pregunta administrativa, se le pasan las reglas del albergue
        try:
            async with aiofiles.open(prompts_dir / "reglas_albergue.txt", "r") as f:
                context = await f.read()
        except Exception:
            context = None

    response_text = ""
    for chunk in llm.generate_response(
        question=request.content,
        prompt=main_prompt, # -> El prompt principal siempre sera el mismo, solo cambia el contexto dado (abajo)
        context=context, # -> Contexto del paciente o albergue (puede ser none, asi que lo dejo asi noma)
        conversation_history=history_text if history_text else None,
    ):
        if chunk:
            response_text += chunk

    ai_message = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=request.session_id,
        role="ai",
        content=response_text,
        created_at=datetime.now(),
    )
    await db.create_chat_message(ai_message)

    return ChatMessageResponse(
        id=ai_message.id,
        session_id=ai_message.session_id,
        role=ai_message.role,
        content=ai_message.content,
        created_at=ai_message.created_at,
    )


@router.post("/doctor/messages", response_model=ChatMessageResponse) # -> Send message (doctor - search by doctor)
async def send_doctor_message(request: SendMessageRequest):
    db = Database()
    await db.connect()

    session = await db.get_chat_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MESSAGE)
    if session.user_id != request.user_id:
        raise HTTPException(status_code=403, detail=NOT_AUTHORIZED_MESSAGE)

    user_message = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=request.session_id,
        role="user",
        content=request.content,
        created_at=datetime.now(),
    )
    await db.create_chat_message(user_message)

    history = await db.get_last_n_messages(request.session_id, n=30)
    history_text = "\n".join(f"{m.role}: {m.content}" for m in history)

    llm = _get_llm()
    prompts_dir = Path(__file__).resolve().parent.parent / "modules" / "chat" / "prompts"

    try:
        async with aiofiles.open(prompts_dir / MAIN_PROMPT_FILE_NAME, "r") as pf:
            main_prompt = await pf.read()
    except Exception:
        main_prompt = None

    intention = final_chat_intention_predictor(llm, request.content)

    context = None
    if intention == "patient_information":
        print("Searching for patient information by doctor in the vector database...")
        try:
            vect_db = VectorDB(pool=db.pool)
            context_chunks = await vect_db.search_by_doctor(query=request.content)
            print(f"Found {len(context_chunks)} context chunks:")
            context = format_chunks_as_context(context_chunks) if context_chunks else None
            print("Context:", context)
        except Exception as e:
            print(f"Vector search error: {e}")
            context = None
    elif intention == "administrative_question":
        try:
            async with aiofiles.open(prompts_dir / "reglas_albergue.txt", "r") as f:
                context = await f.read()
        except Exception:
            context = None

    response_text = ""
    for chunk in llm.generate_response(
        question=request.content,
        prompt=main_prompt,
        context=context,
        conversation_history=history_text if history_text else None,
    ):
        if chunk:
            response_text += chunk

    ai_message = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=request.session_id,
        role="ai",
        content=response_text,
        created_at=datetime.now(),
    )
    await db.create_chat_message(ai_message)

    return ChatMessageResponse(
        id=ai_message.id,
        session_id=ai_message.session_id,
        role=ai_message.role,
        content=ai_message.content,
        created_at=ai_message.created_at,
    )


@router.post("/doctor/messages/patient/{patient_id}", response_model=ChatMessageResponse) # -> Send message (doctor - specific patient)
async def send_doctor_patient_message(request: SendMessageRequest, patient_id: str):
    db = Database()
    await db.connect()

    session = await db.get_chat_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MESSAGE)
    if session.user_id != request.user_id:
        raise HTTPException(status_code=403, detail=NOT_AUTHORIZED_MESSAGE)

    user_message = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=request.session_id,
        role="user",
        content=request.content,
        created_at=datetime.now(),
    )
    await db.create_chat_message(user_message)

    history = await db.get_last_n_messages(request.session_id, n=30)
    history_text = "\n".join(f"{m.role}: {m.content}" for m in history)

    llm = _get_llm()
    prompts_dir = Path(__file__).resolve().parent.parent / "modules" / "chat" / "prompts"

    try:
        async with aiofiles.open(prompts_dir / MAIN_PROMPT_FILE_NAME, "r") as pf:
            main_prompt = await pf.read()
    except Exception:
        main_prompt = None

    context = None
    print(f"Searching for patient {patient_id} information in the vector database...")
    try:
        vect_db = VectorDB(pool=db.pool)
        context_chunks = await vect_db.search_by_patient(
            query=request.content,
            patient_id=patient_id,
        )
        print(f"Found {len(context_chunks)} context chunks:")
        context = format_chunks_as_context(context_chunks) if context_chunks else None
        print("Context:", context)
    except Exception as e:
        print(f"Vector search error: {e}")
        context = None

    response_text = ""
    for chunk in llm.generate_response(
        question=request.content,
        prompt=main_prompt,
        context=context,
        conversation_history=history_text if history_text else None,
    ):
        if chunk:
            response_text += chunk

    ai_message = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=request.session_id,
        role="ai",
        content=response_text,
        created_at=datetime.now(),
    )
    await db.create_chat_message(ai_message)

    return ChatMessageResponse(
        id=ai_message.id,
        session_id=ai_message.session_id,
        role=ai_message.role,
        content=ai_message.content,
        created_at=ai_message.created_at,
    )