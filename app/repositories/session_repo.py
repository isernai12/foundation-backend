import datetime
from typing import Optional, List
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from backend.app.models.auth import UserSession
from backend.app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[UserSession]):
    def __init__(self):
        super().__init__(UserSession)

    def create_session(
        self,
        db: Session,
        user_id: str,
        jti: str,
        expires_at: datetime.datetime,
        device: Optional[str] = None,
        browser: Optional[str] = None,
        os: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> UserSession:
        session = UserSession(
            userId=user_id,
            jti=jti,
            expiresAt=expires_at,
            device=device,
            browser=browser,
            os=os,
            ipAddress=ip_address,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def get_by_jti(self, db: Session, jti: str) -> Optional[UserSession]:
        stmt = select(UserSession).where(UserSession.jti == jti)
        return db.scalars(stmt).first()

    def update_last_active(self, db: Session, jti: str) -> None:
        stmt = select(UserSession).where(UserSession.jti == jti)
        session = db.scalars(stmt).first()
        if session:
            session.lastActive = datetime.datetime.now(datetime.timezone.utc)
            db.commit()

    def delete_by_jti(self, db: Session, jti: str) -> bool:
        stmt = delete(UserSession).where(UserSession.jti == jti)
        result = db.execute(stmt)
        db.commit()
        return result.rowcount > 0

    def delete_user_sessions(self, db: Session, user_id: str) -> int:
        stmt = delete(UserSession).where(UserSession.userId == user_id)
        result = db.execute(stmt)
        db.commit()
        return result.rowcount

    def get_active_user_sessions(self, db: Session, user_id: str) -> List[UserSession]:
        now = datetime.datetime.now(datetime.timezone.utc)
        stmt = (
            select(UserSession)
            .where(UserSession.userId == user_id, UserSession.expiresAt > now)
            .order_by(UserSession.lastActive.desc())
        )
        return list(db.scalars(stmt).all())


session_repo = SessionRepository()
