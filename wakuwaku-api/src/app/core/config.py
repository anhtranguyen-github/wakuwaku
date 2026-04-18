from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    API_V1_STR: str = "/v2"
    PROJECT_NAME: str = "WakuWaku WaniKani"
    VERSION: str = "20170710"

    # Supabase (auth + database only)
    SUPABASE_URL: str = "https://example.supabase.co"
    SUPABASE_KEY: str = "your-supabase-key"
    SUPABASE_JWT_SECRET: str = "your-jwt-secret"

    # Application base URL (used for profile_url, resource URLs, etc.)
    APP_BASE_URL: str = "http://localhost:8000"

    # WaniKani API (for crawl/sync)
    WANIKANI_API_URL: str = "https://api.wanikani.com/v2"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
