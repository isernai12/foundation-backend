import datetime
import uuid
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.auth import User
from app.schemas.auth import UserProfile, TokenResponse
from app.repositories import user_repo, session_repo, audit_repo
from app.auth.security import (
    verify_password,
    create_access_token,
    parse_user_agent,
)


class AuthService:
    def authenticate(
        self,
        db: Session,
        username: str,
        password: str,
        remember_me: bool = False,
        client_info: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, UserProfile, int, str]:
        """
        Authenticates a user via username or email and plaintext password.
        Creates a server-side session and generates a signed JWT token.
        """
        info = client_info or {}
        ip_address = info.get("ip_address", "Unknown")
        user_agent_str = info.get("user_agent", "Unknown")
        ua_details = parse_user_agent(user_agent_str)

        # 1. Lookup user by username or email
        user = user_repo.get_by_username_or_email(db, username)

        if not user:
            # Mask failure detail to prevent enumeration
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive or suspended",
            )

        # 2. Verify bcrypt password
        if not verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 3. Calculate expiration
        duration_minutes = (
            settings.REMEMBER_ME_EXPIRE_MINUTES
            if remember_me
            else settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        expires_delta = datetime.timedelta(minutes=duration_minutes)
        expires_at = datetime.datetime.now(datetime.timezone.utc) + expires_delta
        expires_in_seconds = int(expires_delta.total_seconds())

        # 4. Generate unique session ID (JTI)
        jti = str(uuid.uuid4())

        # 5. Persist server-side session
        session_repo.create_session(
            db=db,
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
            device=ua_details["device"],
            browser=ua_details["browser"],
            os=ua_details["os"],
            ip_address=ip_address,
        )

        # 6. Record Audit Log
        audit_repo.log(
            db=db,
            action="LOGIN",
            module="AUTHENTICATION",
            user_id=user.id,
            ip_address=ip_address,
            device=ua_details["device"],
            browser=ua_details["browser"],
            remarks="User authenticated successfully",
        )

        # 7. Update user last login
        user_repo.update_last_login(db, user.id)

        # 8. Load permissions
        permissions = user_repo.get_user_permissions(db, user.id)

        # 9. Create JWT token
        token_payload = {
            "sub": user.id,
            "username": user.username,
            "name": user.name,
            "role": user.role.name if user.role else "UNKNOWN",
        }
        access_token = create_access_token(
            data=token_payload,
            expires_delta=expires_delta,
            jti=jti,
        )

        user_profile = UserProfile(
            id=user.id,
            name=user.name,
            username=user.username,
            email=user.email,
            mobile=user.mobile,
            role=user.role.name if user.role else "UNKNOWN",
            status=user.status,
            photo=user.photo,
            preferences=user.preferences,
            permissions=permissions,
        )

        return access_token, user_profile, expires_in_seconds, jti

    def logout(self, db: Session, jti: str, user_id: Optional[str] = None) -> bool:
        """
        Invalidates a session token server-side by deleting the UserSession record.
        """
        if jti:
            session_repo.delete_by_jti(db, jti)
        if user_id:
            audit_repo.log(
                db=db,
                action="LOGOUT",
                module="AUTHENTICATION",
                user_id=user_id,
                remarks=f"Session {jti} terminated",
            )
        return True

    def get_user_profile(self, db: Session, user_id: str) -> Optional[UserProfile]:
        user = user_repo.get_by_id(db, user_id)
        if not user:
            return None
        permissions = user_repo.get_user_permissions(db, user_id)
        return UserProfile(
            id=user.id,
            name=user.name,
            username=user.username,
            email=user.email,
            mobile=user.mobile,
            role=user.role.name if user.role else "UNKNOWN",
            status=user.status,
            photo=user.photo,
            preferences=user.preferences,
            permissions=permissions,
        )


auth_service = AuthService()
