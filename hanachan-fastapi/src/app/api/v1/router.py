from fastapi import APIRouter
from app.api.v1 import users, hanachan, auth

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(hanachan.router, tags=["Hanachan"])