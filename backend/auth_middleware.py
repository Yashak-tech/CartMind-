"""
FastAPI HTTP Middleware enforcing JWT authentication across all application routes.
Bypasses whitelisted paths (/auth/*, /health, /docs, webhooks, callbacks).
"""

from typing import Set
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from backend.routes.auth import decode_access_token


class AccessGateMiddleware(BaseHTTPMiddleware):
    """
    Validates JWT Bearer tokens on all protected routes.
    Rejects unauthenticated or expired requests with HTTP 401 Unauthorized.
    """

    # Explicitly whitelisted exact paths and path prefixes
    EXACT_WHITELIST: Set[str] = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/auth/request-code",
        "/auth/verify-code",
        "/api/test-payment/callback",
    }

    PREFIX_WHITELIST: Set[str] = (
        "/auth/",
        "/api/webhooks/",
        "/api/test-payment/status/",
    )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Allow all CORS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path

        # 2. Allow whitelisted endpoints
        if path in self.EXACT_WHITELIST:
            return await call_next(request)

        for prefix in self.PREFIX_WHITELIST:
            if path.startswith(prefix):
                return await call_next(request)

        # 3. Extract and validate Bearer token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Access gate token required. Please sign in with an email access code."},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header[7:].strip()
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing bearer token in Authorization header."},
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = decode_access_token(token)
            request.state.user_email = payload.get("sub")
        except Exception as e:
            detail = getattr(e, "detail", "Invalid or expired access token.")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": detail},
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)
