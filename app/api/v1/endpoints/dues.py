from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.auth import User
from backend.app.schemas.dues import (
    SingleDuePayRequest,
    MultiMonthDuePayRequest,
    DuePaymentResponse,
    MemberDuesSummaryResponse,
    MemberDuesLedgerResponse,
)
from backend.app.services.dues_service import dues_service
from backend.app.rbac.dependencies import require_permission

router = APIRouter(tags=["Monthly Dues & Contributions"])


@router.post(
    "/contributions/single",
    response_model=DuePaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Pay Single Month Due",
    description="Collects monthly membership due for a specific month and year, recording balanced double-entry ledger transactions.",
)
def pay_single_month(
    data: SingleDuePayRequest,
    current_user: User = Depends(require_permission("Fund Collection", "Add")),
    db: Session = Depends(get_db),
) -> DuePaymentResponse:
    return dues_service.pay_single_month(
        db=db,
        data=data,
        current_user_id=current_user.id,
    )


@router.post(
    "/contributions/advance",
    response_model=DuePaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Pay Multi-Month Advance Dues",
    description="Collects advance dues for an explicit range (from_month/from_year to to_month/to_year) across year boundaries.",
)
def pay_multi_month_advance(
    data: MultiMonthDuePayRequest,
    current_user: User = Depends(require_permission("Fund Collection", "Add")),
    db: Session = Depends(get_db),
) -> DuePaymentResponse:
    return dues_service.pay_multi_month_advance(
        db=db,
        data=data,
        current_user_id=current_user.id,
    )


@router.get(
    "/members/{member_id}/dues",
    response_model=MemberDuesSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Member Dues Summary",
    description="Retrieves a member's dues overview, current monthly fee, paidUntil status, total paid, and outstanding dues.",
)
def get_member_dues_summary(
    member_id: str,
    current_user: User = Depends(require_permission("Members", "View")),
    db: Session = Depends(get_db),
) -> MemberDuesSummaryResponse:
    return dues_service.get_member_dues_summary(db=db, member_id=member_id)


@router.get(
    "/members/{member_id}/dues/ledger",
    response_model=MemberDuesLedgerResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Member Dues Ledger",
    description="Retrieves chronological payment records and dues ledger for a specific member.",
)
def get_member_dues_ledger(
    member_id: str,
    year: Optional[int] = Query(None, description="Filter by calendar year"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_permission("Members", "View")),
    db: Session = Depends(get_db),
) -> MemberDuesLedgerResponse:
    return dues_service.get_member_dues_ledger(
        db=db,
        member_id=member_id,
        year=year,
        page=page,
        page_size=page_size,
    )
