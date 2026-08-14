from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.auth import User
from backend.app.schemas.role import PermissionListResponse
from backend.app.services.role_service import role_service
from backend.app.rbac.dependencies import require_permission

router = APIRouter(prefix="/permissions", tags=["Roles & Permissions Management"])


@router.get(
    "",
    response_model=PermissionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List System Permissions",
    description="Retrieves all registered system permissions grouped by module with machine-readable codes and localized titles.",
)
def list_permissions(
    current_user: User = Depends(require_permission("Roles & Permissions", "View")),
    db: Session = Depends(get_db),
) -> PermissionListResponse:
    return role_service.list_permissions(db=db)


@router.post(
    "/sync",
    status_code=status.HTTP_200_OK,
    summary="Sync System Permissions",
    description="Idempotently ensures all canonical system permissions exist in the database without altering existing records.",
)
def sync_permissions(
    current_user: User = Depends(require_permission("Roles & Permissions", "Manage")),
    db: Session = Depends(get_db),
) -> dict:
    inserted = role_service.sync_permissions(db=db)
    return {
        "success": True,
        "new_permissions_inserted": inserted,
        "message": f"Successfully synced system permissions ({inserted} new created).",
    }
