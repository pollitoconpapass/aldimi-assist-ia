from fastapi import APIRouter
from modules.data.sql_db import Database

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
async def get_users():
    db = Database()
    await db.connect()
    users = await db.list_users()
    return users

@router.get("/{user_id}")
async def get_user(user_id: str):
    db = Database()
    await db.connect()
    user = await db.get_user(user_id)
    return user

@router.get("/email/{email}")
async def get_user_by_email(email: str):
    db = Database()
    await db.connect()
    user = await db.get_user_by_email(email)
    return user

@router.get("/role/{role}")
async def get_users_by_role(role: str):
    db = Database()
    await db.connect()
    users = await db.list_users_by_role(role)
    return users

@router.put("/{user_id}")
async def update_user(user_id: str, user: dict):
    db = Database()
    await db.connect()
    updated_user = await db.update_user(user_id, **user)
    return updated_user

@router.delete("/{user_id}")
async def delete_user(user_id: str):
    db = Database()
    await db.connect()
    deleted = await db.delete_user(user_id)
    return {"deleted": deleted}