from fastapi import APIRouter, status, HTTPException
from app.services.hanachan_service import HanachanService
from app.schemas.user import UserCreate, UserLogin
from app.db import get_supabase

router = APIRouter()


@router.post("/standalone/register", status_code=status.HTTP_201_CREATED)
async def register_standalone(user_in: UserCreate):
    """
    Register a new user with Supabase Auth and seed Level 1 data.
    """
    supabase = get_supabase()
    
    try:
        # 1. Register with Supabase Auth
        # Note: Depending on Supabase settings, this might require email confirmation.
        # If site_url and other settings are configured, this returns a user object.
        auth_response = supabase.auth.sign_up({
            "email": user_in.email,
            "password": user_in.password,
            "options": {
                "data": {
                    "username": user_in.username or user_in.email.split("@")[0]
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Registration failed")
            
        user_id = auth_response.user.id
        
        # 2. Seed Hanachan data
        service = HanachanService(supabase, user_id)
        await service.seed_standalone_user()
        
        # 3. Return session/token if available, otherwise just signal success
        token = auth_response.session.access_token if auth_response.session else user_id
        
        return {
            "user_id": user_id,
            "token": token,
            "type": "standalone"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/standalone/login")
async def login_standalone(credentials: UserLogin):
    """
    Login with email/password via Supabase Auth.
    """
    supabase = get_supabase()
    
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        
        if not auth_response.session:
            raise HTTPException(status_code=401, detail="Invalid credentials or email not confirmed")
            
        return {
            "user_id": auth_response.user.id,
            "token": auth_response.session.access_token,
            "type": "standalone"
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
