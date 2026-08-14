from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.auth import User
from backend.app.schemas.group import (
    GroupCreateRequest,
    GroupUpdateRequest,
    GroupResponse,
    GroupListResponse,
)
from backend.app.services.group_service import group_service
from backend.app.rbac.dependencies import require_permission

router = APIRouter(prefix="/groups", tags=["Groups / Villages"])


@router.get(
    "",
    response_model=GroupListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Groups / Villages",
    description="Retrieves a paginated list of groups with search and signup-enabled filters.",
)
def list_groups(
    query: Optional[str] = Query(None, description="Search by group name, code, short name"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, INACTIVE)"),
    member_signup_enabled: Optional[bool] = Query(None, description="Filter by public signup eligibility"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_permission("Groups", "View")),
    db: Session = Depends(get_db),
) -> GroupListResponse:
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
