from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.auth import User
from backend.app.schemas.member_request import (
    MemberRequestCreate,
    MemberRequestApprove,
    MemberRequestReject,
    MemberRequestSubmitResponse,
    MemberRequestStatusResponse,
    MemberRequestDetailResponse,
    MemberRequestListResponse,
)
from backend.app.services.member_request_service import member_request_service
from backend.app.rbac.dependencies import require_permission

router = APIRouter(prefix="/member-requests", tags=["Member Requests"])


# ---------------------------------------------------------------------------
# PUBLIC ENDPOINTS
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=MemberRequestSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Member Request (Public)",
    description="Public endpoint allowing prospective members to apply with personal, contact, and document details.",
)
def submit_member_request(
    data: MemberRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> MemberRequestSubmitResponse:
    client_info = {
        "ip_address": request.client.host if request.client else "Unknown",
        "user_agent": request.headers.get("user-agent", "Unknown"),
    }
    return member_request_service.submit_public_request(db=db, data=data, client_info=client_info)


@router.get(
    "/{identifier}/status",
    response_model=MemberRequestStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check Application Status (Public)",
    description="Public endpoint allowing applicants to check approval status by application number (e.g. MR-2026-00001) or UUID.",
)
def get_member_request_status(
    identifier: str,
    db: Session = Depends(get_db),
) -> MemberRequestStatusResponse:
    return member_request_service.get_status(db=db, identifier=identifier)


# ---------------------------------------------------------------------------
# ADMIN / AUTHENTICATED WORKFLOW ENDPOINTS
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=MemberRequestListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Member Requests",
    description="Admin endpoint to list and filter submitted applications with search and pagination.",
)
def list_member_requests(
    status: Optional[str] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED, NEEDS_CHANGES)"),
    group_id: Optional[str] = Query(None, description="Filter by requested group UUID"),
    query: Optional[str] = Query(None, description="Search by applicant name, application number, or mobile"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_permission("Members", "View")),
    db: Session = Depends(get_db),
) -> MemberRequestListResponse:
    return member_request_service.list_requests(
        db=db,
        status_filter=status,
        group_id=group_id,
        query=query,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{request_id}",
    response_model=MemberRequestDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Member Request Detail",
    description="Admin endpoint returning full details, attached documents, and approval workflow status of an application.",
)
def get_member_request_detail(
    request_id: str,
    current_user: User = Depends(require_permission("Members", "View")),
    db: Session = Depends(get_db),
) -> MemberRequestDetailResponse:
    return member_request_service.get_request_detail(db=db, request_id=request_id)


@router.post(
    "/{request_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Approve Member Request",
    description="Transactionally approves an application: creates active Member with next Member ID, copies documents, updates request status.",
)
def approve_member_request(
    request_id: str,
    body: Optional[MemberRequestApprove] = None,
    current_user: User = Depends(require_permission("Members", "Add")),
    db: Session = Depends(get_db),
):
    remarks = body.remarks if body else None
    return member_request_service.approve_request(
        db=db,
        request_id=request_id,
        approver=current_user,
        remarks=remarks,
    )


@router.post(
    "/{request_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Reject Member Request",
    description="Rejects a member application with a mandatory reason and optional admin message.",
)
def reject_member_request(
    request_id: str,
    body: MemberRequestReject,
    current_user: User = Depends(require_permission("Members", "Edit")),
    db: Session = Depends(get_db),
):
    return member_request_service.reject_request(
        db=db,
        request_id=request_id,
        reason=body.reason,
        admin_message=body.admin_message,
        rejecter=current_user,
    )
