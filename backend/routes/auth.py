"""
Authentication and Email OTP Access-Gate Router for CartMind.
Handles single-tenant access gate requests, OTP generation via Resend (with dev fallback),
and signed JWT token issuance.
"""

import time
import random
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import httpx
import jwt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.config import settings
from backend.rate_limiter import InMemoryRateLimiter

logger = logging.getLogger("cartmind.auth")

router = APIRouter(prefix="/auth", tags=["Access Gate"])

# Rate limiter for OTP requests: Max 3 requests per 10 minutes (600 seconds) per email
otp_rate_limiter = InMemoryRateLimiter(requests_per_minute=3, window_seconds=600)

# In-memory OTP store: { email: { "code": str, "expires_at": float } }
_otp_store: Dict[str, Dict[str, Any]] = {}


class RequestCodePayload(BaseModel):
    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Recipient email address for single-use access code"
    )


class VerifyCodePayload(BaseModel):
    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Recipient email address"
    )
    code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")


def create_access_token(email: str) -> str:
    """Generates a signed, short-lived JWT token with email subject."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    payload = {
        "sub": email,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "iss": "cartmind-gate",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token; raises HTTPException 401 if invalid or expired."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def _send_resend_email(email: str, code: str) -> bool:
    """Dispatches 6-digit access code via Resend transactional email API."""
    if not settings.RESEND_API_KEY:
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0A0D14; color: #FFFFFF; padding: 40px; border-radius: 12px; max-width: 500px; margin: 0 auto; border: 1px solid #1E293B;">
      <div style="margin-bottom: 24px;">
        <span style="color: #FFB800; font-weight: 800; font-size: 20px; letter-spacing: -0.5px;">CARTMIND</span>
        <span style="color: #94A3B8; font-size: 13px; margin-left: 8px;">• AI Commerce Preview</span>
      </div>
      <h2 style="font-size: 22px; font-weight: 700; margin-bottom: 8px; color: #FFFFFF;">Your Single-Use Access Code</h2>
      <p style="color: #94A3B8; font-size: 14px; line-height: 1.5; margin-bottom: 24px;">
        Use the verification code below to access the CartMind preview workspace. This code is valid for 10 minutes.
      </p>
      <div style="background-color: #111827; border: 1px solid #FFB800; border-radius: 8px; padding: 20px; text-align: center; margin-bottom: 24px;">
        <span style="font-family: monospace; font-size: 36px; font-weight: 900; letter-spacing: 8px; color: #FFB800;">{code}</span>
      </div>
      <p style="color: #64748B; font-size: 12px; line-height: 1.4;">
        If you did not request this access code, please disregard this email. All transactions in this environment operate strictly under Razorpay Test Mode.
      </p>
    </div>
    """

    data = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [email],
        "subject": f"Your CartMind Access Code: {code}",
        "html": html_body,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=data)
            if resp.status_code in (200, 201):
                logger.info(f"Resend email dispatched successfully to {email}")
                return True
            else:
                logger.warning(f"Resend API error {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to communicate with Resend API: {e}")
        return False


@router.post("/request-code", status_code=status.HTTP_200_OK)
async def request_access_code(payload: RequestCodePayload):
    """
    Generates a 6-digit access code for the provided email.
    Dispatches via Resend API (or logs to console if no API key is set).
    Rate-limited to 3 requests per 10 minutes per email.
    """
    clean_email = payload.email.strip().lower()

    # Rate limiting check: 3 requests per 10 minutes per email
    try:
        otp_rate_limiter.check(clean_email)
    except HTTPException as e:
        # Re-raise with email-specific description
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many access code requests for this email. Please wait a few minutes before trying again.",
            headers=e.headers
        )

    # Generate 6-digit numeric code
    code = f"{random.randint(100000, 999999):06d}"
    expires_at = time.time() + (settings.OTP_EXPIRY_MINUTES * 60)

    # Store in memory
    _otp_store[clean_email] = {
        "code": code,
        "expires_at": expires_at,
    }

    # Dispatch email via Resend
    email_sent = await _send_resend_email(clean_email, code)

    # Always log to console for development auditability and test runner visibility
    logger.info(f"[AUTH ACCESS CODE] Code for '{clean_email}': {code} (expires in {settings.OTP_EXPIRY_MINUTES}m)")

    response_data: Dict[str, Any] = {
        "status": "code_sent",
        "email": clean_email,
        "expires_in_minutes": settings.OTP_EXPIRY_MINUTES,
        "email_dispatched": email_sent,
    }

    # In development or when no Resend key is provided, return dev_code for instant local testing
    if not settings.RESEND_API_KEY or settings.ENVIRONMENT == "development":
        response_data["dev_code"] = code

    return response_data


@router.post("/verify-code", status_code=status.HTTP_200_OK)
def verify_access_code(payload: VerifyCodePayload):
    """
    Verifies the 6-digit code for the email.
    If valid, returns a signed JWT token valid for 24 hours.
    """
    clean_email = payload.email.strip().lower()
    clean_code = payload.code.strip()

    record = _otp_store.get(clean_email)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active access code found for this email. Please request a new code."
        )

    if time.time() > record["expires_at"]:
        _otp_store.pop(clean_email, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access code has expired. Please request a new code."
        )

    if record["code"] != clean_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid access code. Please check your email and try again."
        )

    # Code is valid -> consume it (single-use)
    _otp_store.pop(clean_email, None)

    # Generate signed JWT
    token = create_access_token(clean_email)

    return {
        "token": token,
        "email": clean_email,
        "token_type": "bearer",
        "expires_in_hours": settings.JWT_EXPIRY_HOURS,
    }
