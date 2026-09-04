"""
Configuration settings for CartMind backend.
Loads environment variables from .env file with pydantic-settings.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and API keys for local development and evaluator review."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application settings
    APP_NAME: str = "CartMind Backend"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    BASE_URL: str = "http://localhost:8000"

    # CORS Allowed Origins (Hardened: Explicit origins only, no wildcard '*')
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins(self) -> list[str]:
        """
        Returns explicit list of allowed origins.
        Does NOT use wildcard '*'. Restricted to local Vite development origins.
        """
        origins: list[str] = []
        if self.ALLOWED_ORIGINS:
            for item in self.ALLOWED_ORIGINS.split(","):
                cleaned = item.strip().rstrip("/")
                if cleaned and cleaned != "*" and cleaned not in origins:
                    origins.append(cleaned)
        return origins or ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Razorpay Test Credentials (TEST MODE ONLY)
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None

    # Groq API Key (Phase 3 LLM reasoning; offline fallback operates without key)
    GROQ_API_KEY: Optional[str] = None

    # Access Gate Authentication (Email OTP & JWT)
    JWT_SECRET: str = "cartmind_super_secret_jwt_access_key_2026"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24
    OTP_EXPIRY_MINUTES: int = 10

    # Resend Transactional Email API (Optional - Console Fallback in Dev)
    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM_EMAIL: str = "CartMind Access <onboarding@resend.dev>"

    @property
    def has_razorpay_credentials(self) -> bool:
        """Returns True if Razorpay key id and secret are provided."""
        return bool(self.RAZORPAY_KEY_ID and self.RAZORPAY_KEY_SECRET)


settings = Settings()
