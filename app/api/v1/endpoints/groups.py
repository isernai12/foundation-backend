from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.auth import User
from app.auth.dependencies import extract_token_from_request, get_current_user, get_current_active_user
from app.repositories import user_repo
from app.rbac.service import is_super_admin, has_permission
from app.schemas.group import (
    GroupCreateRequest,
    GroupUpdateRequest,
    GroupResponse,
    GroupListResponse,
)
from app.services.group_service import group_service
from app.rbac.dependencies import require_permission

router = APIRouter(prefix="/groups", tags=["Groups / Villages"])


@router.get(
    "",
    response_model=GroupListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Groups / Villages",
    description="Retrieves a paginated list of groups with search and signup-enabled filters.",
)
def list_groups(
    request: Request,
    query: Optional[str] = Query(None, description="Search by group name, code, short name"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, INACTIVE)"),
    member_signup_enabled: Optional[bool] = Query(None, description="Filter by public signup eligibility"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=1000, description="Items per page"),
    token: Optional[str] = Depends(extract_token_from_request),
    db: Session = Depends(get_db),
) -> GroupListResponse:
    if member_signup_enabled is True and not token:
        # Public registration / signup-eligible groups query
        return group_service.list_groups(
            db=db,
            query=query,
            status_filter="ACTIVE",
            signup_enabled=True,
            page=page,
            page_size=page_size,
        )

    # For general group queries, require authenticated user with appropriate permissions
    current_user = get_current_active_user(get_current_user(request=request, token=token, db=db))
    user_role = current_user.role.name if current_user.role else None

    if not is_super_admin(user_role):
        permissions = user_repo.get_user_permissions(db, current_user.id)
        if not (
            has_permission(permissions, "Groups", "View", user_role)
            or has_permission(permissions, "Members", "View", user_role)
            or has_permission(permissions, "Members", "Add", user_role)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Groups:View or Members:View required",
            )

    return group_service.list_groups(
        db=db,
        query=query,
        status_filter=status,
        signup_enabled=member_signup_enabled,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{group_id}",
    response_model=GroupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Group Detail",
    description="Retrieves single group details, member count, and current fund balance.",
)
def get_group(
    group_id: str,
    current_user: User = Depends(require_permission("Groups", "View")),
    db: Session = Depends(get_db),
) -> GroupResponse:
    return group_service.get_group(db=db, group_id=group_id)


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Group",
    description="Creates a new village group or branch with unique code validation and signup policy.",
)
def create_group(
    data: GroupCreateRequest,
    current_user: User = Depends(require_permission("Groups", "Add")),
    db: Session = Depends(get_db),
) -> GroupResponse:
    return group_service.create_group(db=db, data=data, current_user_id=current_user.id)


@router.patch(
    "/{group_id}",
    response_model=GroupResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Group",
    description="Updates group information, name, status, or signup enablement.",
)
def update_group(
    group_id: str,
    data: GroupUpdateRequest,
    current_user: User = Depends(require_permission("Groups", "Edit")),
    db: Session = Depends(get_db),
) -> GroupResponse:
    return group_service.update_group(
        db=db,
        group_id=group_id,
        data=data,
        current_user_id=current_user.id,
    )


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_200_OK,
    summary="Hard Delete Group",
    description="Permanently deletes a group and all associated records within an atomic database transaction.",
)
def delete_group(
    group_id: str,
    current_user: User = Depends(require_permission("Groups", "Delete")),
    db: Session = Depends(get_db),
) -> dict:
    return group_service.hard_delete_group(
        db=db,
        group_id=group_id,
        current_user_id=current_user.id,
    )
