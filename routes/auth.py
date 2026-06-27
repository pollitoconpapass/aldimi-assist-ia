import uuid
from fastapi import APIRouter, HTTPException
from schemas.db_schemas import User
from schemas.api_schemas import SignupRequest, LogInRequest
from modules.data.sql_db import Database
from helpers.auth_helpers import hash_password, verify_password
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup")
async def signup(request:SignupRequest) -> User:
    try: 
        db = Database()
        await db.connect()

        exists = await db.get_user_by_dni(request.dni)
        if exists:
            raise HTTPException(status_code=400, detail="User already exists")
        
        user = User(
            id=str(uuid.uuid4()),
            dni=request.dni,
            email=request.email,
            password_hash=hash_password(request.password),
            firstname=request.firstname,
            lastname=request.lastname,
            birthdate=request.birthdate,
            gender=request.gender,
            address=request.address,
            phone=request.phone,
            role=request.role,
            created_at=datetime.now()
        )

        await db.create_user(user)
        
        print("Usuario registrado exitosamente!")
        return { "id": user.id, "status_code": 201}
    except Exception as e:
        print("Error al registrar el usuario: ", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(request: LogInRequest) -> User:
    db = Database()
    await db.connect()

    user = await db.get_user_by_email(request.email)
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return user
