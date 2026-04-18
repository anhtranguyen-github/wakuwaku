import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg2
from jose import jwt
from passlib.context import CryptContext
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, status, HTTPException

from app.core.config import settings
from app.schemas.user import UserCreate, UserLogin

router = APIRouter()

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def get_db_conn():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


@router.post("/standalone/register", status_code=status.HTTP_201_CREATED)
async def register_standalone(user_in: UserCreate):
    username = user_in.username or user_in.email.split("@")[0]
    password_hash = pwd_context.hash(user_in.password)
    user_id = str(uuid4())

    try:
        with get_db_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (
                    id, username, email, password_hash,
                    level, max_level_granted, subscription_type,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, 1, 60, 'free', NOW(), NOW())
                RETURNING id
                """,
                (user_id, username, user_in.email, password_hash),
            )
            row = cur.fetchone()

        token = create_access_token(user_id)
        return {
            "user_id": row["id"],
            "token": token,
            "type": "standalone"
        }
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=400, detail="Email already registered")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/standalone/login")
async def login_standalone(credentials: UserLogin):
    try:
        with get_db_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, password_hash
                FROM users
                WHERE lower(email) = lower(%s)
                LIMIT 1
                """,
                (credentials.email,),
            )
            user = cur.fetchone()

        if not user or not user["password_hash"]:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not pwd_context.verify(credentials.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token(str(user["id"]))
        return {
            "user_id": user["id"],
            "token": token,
            "type": "standalone"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
