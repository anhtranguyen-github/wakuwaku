from fastapi import HTTPException, status
from supabase import Client
from app.schemas.user import UserCreate

class UserService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def create_user(self, user_in: UserCreate):
        try:
            # Note: auth.sign_up is typically synchronous in the supabase python client
            # but wrapping it in try/except is good practice for error handling.
            res = self.supabase.auth.sign_up({
                "email": user_in.email,
                "password": user_in.password
            })
            if not res.user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user"
                )
            return res.user
        except Exception as e:
            # Broad exception catch to handle supabase exceptions
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
