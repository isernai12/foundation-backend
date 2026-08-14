from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.auth import User
from backend.app.schemas.role import (
    RoleCreateRequest,
    RoleUpdateRequest,
    RoleDetailResponse,
    RoleListResponse,
)
from backend.app.services.role_service import role_service
from backend.app.rbac.dependencies import require_permission

router = APIRouter(prefix="/roles", tags=["Roles & Permissions Management"])


@router.get(
    "",
    response_model=RoleListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Roles",
    description="Retrieves all system and custom roles with user counts and assigned permissions count.",
)
def list_roles(
    current_user: User = Depends(require_permission("Roles & Permissions", "View")),
    db: Session = Depends(get_db),
) -> RoleListResponse:
    return role_service.list_roles(db=db)


@router.get(
    "/{role_id}",
    response_model=RoleDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Role Details",
    description="Retrieves details and assigned permissions for a specific role.",
)
def get_role(
    role_id: str,
    current_user: User = Depends(require_permission("Roles & Permissions", "View")),
    db: Session = Depends(get_db),
) -> RoleDetailResponse:
    return role_service.get_role(db=db, role_id=role_id)


@router.post(
    "",
    response_model=RoleDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Role",
    description="Creates a new custom role and assigns permissions.",
)
def create_role(
    data: RoleCreateRequest,
    current_user: User = Depends(require_permission("Roles & Permissions", "Add")),
    db: Session = Depends(get_db),
) -> RoleDetailResponse:
    return role_service.create_role(
        db=db,
        data=data,
        current_user_id=current_user.id,
    )


@router.patch(
    "/{role_id}",
    response_model=RoleDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Role",
    description="Updates role details or modifies assigned permissions.",
)
def update_role(
    role_id: str,
    data: RoleUpdateRequest,
    current_user: User = Depends(require_permission("Roles & Permissions", "Edit")),
    db: Session = Depends(get_db),
) -> RoleDetailResponse:
    return role_service.update_role(
        db=db,
        role_id=role_id,
        data=data,
        current_user_id=current_user.id,
    )


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Role",
    description="Deletes a custom role (safeguarded against Super Admin and roles with assigned users).",
)
def delete_role(
    role_id: str,
    current_user: User = Depends(require_permission("Roles & Permissions", "Delete")),
    db: Session = Depends(get_db),
) -> dict:
    return role_service.delete_role(
        db=db,
        role_id=role_id,
        current_user_id=current_user.id,
    )
