import datetime
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.auth import User
from app.repositories import user_repo, session_repo
from app.auth.security import decode_access_token

# Optional bearer scheme (does not auto-raise 403 so cookie fallback can be checked)
bearer_scheme = HTTPBearer(auto_error=False)


def ensure_utc(dt: datetime.datetime) -> datetime.datetime:
    """Helper to ensure datetime is timezone-aware UTC for cross-database compatibility."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def extract_token_from_request(
    request: Request,
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[str]:
    """
    Extracts authentication token from Authorization Bearer header or HTTP-only cookies.
    Supports both backend cookie names and legacy NextAuth session cookie names.
    """
    # 1. Check Bearer token in header
    if bearer_creds and bearer_creds.credentials:
        return bearer_creds.credentials

    # 2. Check primary session cookie
    cookie_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    # 3. Check legacy/NextAuth cookie names for transition compatibility
    nextauth_token = request.cookies.get("__Secure-next-auth.session-token") or request.cookies.get(
        "next-auth.session-token"
    )
    if nextauth_token:
        return nextauth_token

    return None


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(extract_token_from_request),
    db: Session = Depends(get_db),
) -> User:
    """
    Validates token and returns the current authenticated User model.
    Validates server-side session existence via JTI to support instantaneous revocation.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = payload.get("sub")
    jti: Optional[str] = payload.get("jti")

    if not user_id or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate server-side session in database
    session_record = session_repo.get_by_jti(db, jti)
    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check expiration safely
    now = datetime.datetime.now(datetime.timezone.utc)
    session_expires = ensure_utc(session_record.expiresAt)
    if session_expires < now:
        session_repo.delete_by_jti(db, jti)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user
    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Store active jti on request state for logout / audit purposes
    request.state.session_jti = jti
    request.state.user = user

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensures current user has status == ACTIVE.
    """
    if current_user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or suspended",
        )
    return current_user
