import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_file_path = os.path.join(_backend_dir, ".env")

class Settings(BaseSettings):
    # App
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_API_KEY_SID: Optional[str] = None
    TWILIO_API_KEY_SECRET: Optional[str] = None
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_WEBHOOK_URL: str = "http://localhost:8000"
    TWILIO_WHATSAPP_NUMBER: str = "whatsapp:+14155238886"

    # Gnani AI (Prisma STT + Timbre TTS)
    GNANI_API_KEY: str = ""
    GNANI_STT_WS_URL: str = "wss://api.vachana.ai/stt/v3/stream"
    GNANI_TTS_API_URL: str = "https://api.vachana.ai/api/v1/tts/inference"
    GNANI_STT_LANG: str = "hin-eng" # Hindi, English, Hinglish
    GNANI_TTS_VOICE: str = "Shubham"

    # LLM (Google Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    # Email
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "orders@curatedindia.com"
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./barta.db"
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None

    # Safety & Window
    DEFAULT_WINDOW_START: str = "09:00"
    DEFAULT_WINDOW_END: str = "20:00"
    DEFAULT_MAX_CONCURRENT: int = 1

    model_config = SettingsConfigDict(
        env_file=(_env_file_path, "backend/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

