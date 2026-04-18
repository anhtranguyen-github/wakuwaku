from supabase import create_client, Client
from app.core.config import settings

# Supabase Client Initialization
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def get_supabase() -> Client:
    """
    Dependency for fetching the Supabase client.
    """
    return supabase
