from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5433/hanachan"
    API_V1_STR: str = "/v2"
    PROJECT_NAME: str = "Hanachan Hanachan WaniKani"
    VERSION: str = "20170710"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
