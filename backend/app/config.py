from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    APP_NAME: str = "Major Project"
    APP_ENV: str = "development"
    DEBUG: bool = True
    STORAGE_DIR: str = "storage"
    UPLOAD_DIR: str = "storage/uploads"
    STEGO_DIR: str = "storage/stego"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()