from datetime import datetime, timedelta, timezone

from jose import jwt
from supabase import create_client, Client
from app.core.config import settings


def _build_supabase_key() -> str:
    key = settings.SUPABASE_KEY
    if key.count(".") == 2:
        return key

    now = datetime.now(timezone.utc)
    payload = {
        "role": "anon",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=3650)).timestamp()),
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


# Supabase Client Initialization
supabase: Client = create_client(settings.SUPABASE_URL, _build_supabase_key())


def get_supabase() -> Client:
    """
    Dependency for fetching the Supabase client.
    """
    return supabase
