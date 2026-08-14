from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.auth import User, UserSession
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserProfile,
    LogoutResponse,
    SessionInfo,
    SessionListResponse,
    ChangePasswordRequest,
    UpdateProfileRequest,
    UpdatePreferencesRequest,
)
from app.auth.service import auth_service
from app.auth.dependencies import get_current_active_user
from app.repositories import session_repo, audit_repo
from app.auth.security import verify_password, get_password_hash

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


@router.get(
    "/devices",
    response_model=SessionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Active User Devices",
    description="Returns all active sessions and device information for the current user.",
)
def get_active_devices(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SessionListResponse:
    sessions = session_repo.get_active_user_sessions(db, current_user.id)
    current_jti: Optional[str] = getattr(request.state, "session_jti", None)
    items = [
        SessionInfo(
            id=s.id,
            jti=s.jti,
            device=s.device,
            browser=s.browser,
            os=s.os,
            ip_address=s.ipAddress,
            last_active=s.lastActive,
            expires_at=s.expiresAt,
        )
        for s in sessions
    ]
    return SessionListResponse(sessions=items, current_jti=current_jti)


@router.delete(
    "/devices/{jti}",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke Specific Device Session",
)
def revoke_device(
    jti: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    session_repo.delete_by_jti(db, jti)
    return LogoutResponse(status="ok", message=f"Session {jti} revoked")


@router.delete(
    "/devices",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke All Other User Sessions",
)
def revoke_other_devices(
    request: Request,
    all_devices: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    current_jti: Optional[str] = getattr(request.state, "session_jti", None)
    if all_devices:
        session_repo.delete_user_sessions(db, current_user.id)
    elif current_jti:
        stmt = delete(UserSession).where(
            UserSession.userId == current_user.id,
            UserSession.jti != current_jti,
        )
        db.execute(stmt)
        db.commit()
    return LogoutResponse(status="ok", message="Sessions revoked successfully")


@router.post(
    "/change-password",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Change User Password",
)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    if not verify_password(data.current_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    current_user.password = get_password_hash(data.new_password)
    session_repo.delete_user_sessions(db, current_user.id)
    audit_repo.log(db, action="CHANGE_PASSWORD", module="AUTHENTICATION", user_id=current_user.id)
    db.commit()
    return LogoutResponse(status="ok", message="Password changed successfully. Please log in again.")


@router.patch(
    "/preferences",
    response_model=UserProfile,
    status_code=status.HTTP_200_OK,
    summary="Update User Preferences",
)
def update_preferences(
    data: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> UserProfile:
    current_user.preferences = data.preferences
    db.commit()
    db.refresh(current_user)
    return get_me(current_user, db)


@router.patch(
    "/profile",
    response_model=UserProfile,
    status_code=status.HTTP_200_OK,
    summary="Update Profile Details",
)
def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> UserProfile:
    if data.name is not None:
        current_user.name = data.name.strip()
    if data.mobile is not None:
        current_user.mobile = data.mobile.strip() or None
    if data.email is not None:
        current_user.email = data.email.strip() or None
    if data.photo is not None:
        current_user.photo = data.photo.strip() or None
    db.commit()
    db.refresh(current_user)
    return get_me(current_user, db)
