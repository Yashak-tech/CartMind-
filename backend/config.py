"""
Configuration settings for CartMind backend.
Loads environment variables from .env file with pydantic-settings.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and API keys."""

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
    BACKEND_URL: Optional[str] = None
    RENDER_EXTERNAL_URL: Optional[str] = None

    # CORS & Production Frontend Origin
    FRONTEND_URL: Optional[str] = None
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    def model_post_init(self, __context) -> None:
        """Dynamically resolve BASE_URL if BACKEND_URL or RENDER_EXTERNAL_URL is supplied."""
        effective = self.BACKEND_URL or self.RENDER_EXTERNAL_URL
        if effective:
            self.BASE_URL = effective.rstrip("/")

    @property
    def cors_origins(self) -> list[str]:
        """
        Returns the explicit list of allowed origins.
        Does NOT use wildcard '*'. Includes FRONTEND_URL and configured ALLOWED_ORIGINS.
        """
        origins: list[str] = []
        if self.ALLOWED_ORIGINS:
            for item in self.ALLOWED_ORIGINS.split(","):
                cleaned = item.strip().rstrip("/")
                if cleaned and cleaned != "*" and cleaned not in origins:
                    origins.append(cleaned)

        if self.FRONTEND_URL:
            cleaned_front = self.FRONTEND_URL.strip().rstrip("/")
            if cleaned_front and cleaned_front != "*" and cleaned_front not in origins:
                origins.append(cleaned_front)

        # Ensure standard local development ports are reachable in dev
        for dev_host in ["http://localhost:5173", "http://127.0.0.1:5173"]:
            if dev_host not in origins:
                origins.append(dev_host)

        return origins

    # Razorpay Test Credentials (TEST MODE ONLY)
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None

    # Groq API Key (Phase 3)
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
