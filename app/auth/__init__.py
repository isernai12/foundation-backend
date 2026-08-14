"""Authentication package."""
from app.auth.router import router
from app.auth.service import auth_service, AuthService
from app.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    extract_token_from_request,
)
from app.auth.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
)

__all__ = [
    "router",
    "auth_service",
    "AuthService",
    "get_current_user",
    "get_current_active_user",
    "extract_token_from_request",
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_access_token",
]
