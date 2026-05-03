from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # App
    APP_NAME: str = "BPA-Agent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database — SQLite por defecto (dev), PostgreSQL en prod
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/bpa_agent.db"

    # JWT
    SECRET_KEY: str = "dev-secret-key-change-in-production-min-32-chars!!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas (file:// no envía cookies)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Claude API
    ANTHROPIC_API_KEY: str = ""

    # Encryption (Fernet) — para credenciales MCP
    ENCRYPTION_KEY: str = ""

    # Admin bootstrap
    ADMIN_EMAIL: str = "admin@bpa.com"
    ADMIN_PASSWORD: str = "Admin1234!"

    # CORS — en dev se permite cualquier localhost + acceso directo file://
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3333",
        "http://localhost:3334",
        "http://localhost:8001",
        "http://127.0.0.1:3333",
        "http://127.0.0.1:3000",
        "null",   # browsers file:// origin
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
