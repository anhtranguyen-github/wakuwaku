from fastapi import APIRouter, HTTPException, status
from app.schemas.user import UserResponse
import uuid

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(email: str, username: str = None):
    """
    Create a new user (local dev mode).
    In production, integrate with proper auth system.
    """
    user_id = str(uuid.uuid4())
    username = username or email.split("@")[0]
    return {"id": user_id, "email": email, "username": username}
