from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.auth import User
from app.schemas.member import (
    MemberCreateRequest,
    MemberUpdateRequest,
    MemberDetailResponse,
    MemberListResponse,
)
from app.services.member_service import member_service
from app.rbac.dependencies import require_permission

router = APIRouter(prefix="/members", tags=["Members"])


@router.get(
    "",
    response_model=MemberListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Members",
    description="Retrieves a paginated list of members with search, group, status, and member_type filtering.",
)
def list_members(
    query: Optional[str] = Query(None, description="Search by name, memberId, mobile, NID, or email"),
    group_id: Optional[str] = Query(None, description="Filter by group UUID"),
    status: Optional[str] = Query(None, description="Filter by member status (e.g. ACTIVE, INACTIVE)"),
    member_type: Optional[str] = Query(None, description="Filter by member type (e.g. REGULAR, ASSOCIATE)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_permission("Members", "View")),
    db: Session = Depends(get_db),
) -> MemberListResponse:
    return member_service.list_members(
        db=db,
        query=query,
        group_id=group_id,
        status_filter=status,
        member_type=member_type,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{member_id}",
    response_model=MemberDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Member Detail",
    description="Retrieves detailed profile information for a member, including group, documents, and status history.",
)
def get_member(
    member_id: str,
    current_user: User = Depends(require_permission("Members", "View")),
    db: Session = Depends(get_db),
) -> MemberDetailResponse:
    return member_service.get_member(db=db, member_id=member_id)


@router.post(
    "",
    response_model=MemberDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Member",
    description="Creates a new member under an active group with unique validation and sequential ID assignment.",
)
def create_member(
    data: MemberCreateRequest,
    current_user: User = Depends(require_permission("Members", "Add")),
    db: Session = Depends(get_db),
) -> MemberDetailResponse:
    return member_service.create_member(db=db, data=data, current_user_id=current_user.id)


@router.patch(
    "/{member_id}",
    response_model=MemberDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Member",
    description="Updates member demographic, contact, group, and status fields with validation.",
)
def update_member(
    member_id: str,
    data: MemberUpdateRequest,
    current_user: User = Depends(require_permission("Members", "Edit")),
    db: Session = Depends(get_db),
) -> MemberDetailResponse:
    return member_service.update_member(
        db=db,
        member_id=member_id,
        data=data,
        current_user_id=current_user.id,
    )


@router.delete(
    "/{member_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Member",
    description="Soft-deletes a member, updating status to DELETED and recording status history.",
)
def delete_member(
    member_id: str,
    current_user: User = Depends(require_permission("Members", "Delete")),
    db: Session = Depends(get_db),
):
    return member_service.delete_member(db=db, member_id=member_id, current_user_id=current_user.id)
