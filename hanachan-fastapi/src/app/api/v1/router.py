from fastapi import APIRouter
from app.api.v1 import users, hanachan

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(hanachan.router, tags=["Hanachan"])