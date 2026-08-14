from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.auth import AuditLog
from backend.app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self):
        super().__init__(AuditLog)

    def log(
        self,
        db: Session,
        action: str,
        module: str,
        user_id: Optional[str] = None,
        reference_id: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        ip_address: Optional[str] = None,
        device: Optional[str] = None,
        browser: Optional[str] = None,
        remarks: Optional[str] = None,
    ) -> AuditLog:
        audit = AuditLog(
            userId=user_id,
            action=action,
            module=module,
            referenceId=reference_id,
            oldValue=old_value,
            newValue=new_value,
            ipAddress=ip_address,
            device=device,
            browser=browser,
            remarks=remarks,
        )
        db.add(audit)
        try:
            db.commit()
            db.refresh(audit)
        except Exception:
            db.rollback()
        return audit


audit_repo = AuditLogRepository()
