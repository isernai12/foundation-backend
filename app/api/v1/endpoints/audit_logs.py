from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.auth import AuditLog
from app.schemas.audit import AuditLogItem, AuditLogUser
from app.rbac.dependencies import require_permission

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get(
    "",
    response_model=List[AuditLogItem],
    status_code=status.HTTP_200_OK,
    summary="List Audit Logs",
)
def list_audit_logs(
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("Settings", "View")),
) -> List[AuditLogItem]:
    stmt = (
        select(AuditLog)
        .options(joinedload(AuditLog.user))
        .order_by(AuditLog.createdAt.desc())
        .limit(limit)
    )
    logs = db.scalars(stmt).unique().all()
    results = []
    for log in logs:
        user_info = None
        if log.user:
            user_info = AuditLogUser(name=log.user.name, username=log.user.username)
        results.append(
            AuditLogItem(
                id=log.id,
                userId=log.userId,
                action=log.action,
                module=log.module,
                resourceId=log.resourceId,
                oldData=log.oldData,
                newData=log.newData,
                ipAddress=log.ipAddress,
                device=log.device,
                browser=log.browser,
                remarks=log.remarks,
                createdAt=log.createdAt,
                user=user_info,
            )
        )
    return results
