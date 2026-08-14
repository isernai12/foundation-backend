from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.auth import User
from backend.app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserProfile,
    LogoutResponse,
)
from backend.app.auth.service import auth_service
from backend.app.auth.dependencies import get_current_active_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticates user by username/email and password, sets secure HTTP-only cookie, and returns JWT token.",
)
def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    client_info = {
        "ip_address": request.client.host if request.client else "Unknown",
        "user_agent": request.headers.get("user-agent", "Unknown"),
    }

    access_token, user_profile, expires_in, jti = auth_service.authenticate(
        db=db,
        username=login_data.username,
        password=login_data.password,
        remember_me=login_data.remember_me,
        client_info=client_info,
    )

    # Set secure HttpOnly session cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=access_token,
        max_age=expires_in,
        expires=expires_in,
        path="/",
        secure=settings.is_production,
        httponly=True,
        samesite="lax",
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user=user_profile,
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Invalidates current server-side session and clears session cookie.",
)
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    jti: Optional[str] = getattr(request.state, "session_jti", None)
    if jti:
        auth_service.logout(db, jti=jti, user_id=current_user.id)

    # Clear session cookie
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        secure=settings.is_production,
        httponly=True,
        samesite="lax",
    )

    return LogoutResponse(status="ok", message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserProfile,
    status_code=status.HTTP_200_OK,
    summary="Current User Profile",
    description="Returns current authenticated user details and active permissions.",
)
def get_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> UserProfile:
    profile = auth_service.get_user_profile(db, current_user.id)
    if not profile:
        # Fallback
        return UserProfile(
            id=current_user.id,
            name=current_user.name,
            username=current_user.username,
            email=current_user.email,
            mobile=current_user.mobile,
            role=current_user.role.name if current_user.role else "UNKNOWN",
            status=current_user.status,
            photo=current_user.photo,
            preferences=current_user.preferences,
            permissions=[],
        )
    return profile
