from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.auth import User
from app.schemas.financial_activity import (
    FinancialActivityCreate,
    FinancialActivityUpdate,
    FinancialActivityResponse,
    FinancialActivityListResponse,
    FinancialActivityIncomeRequest,
    FinancialActivityDisburseRequest,
    FinancialActivityLedgerResponse,
)
from app.services.financial_activity_service import financial_activity_service
from app.rbac.dependencies import require_permission

router = APIRouter(prefix="/financial-activities", tags=["Financial Activities & Campaigns"])


@router.get(
    "",
    response_model=FinancialActivityListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Financial Activities",
    description="Retrieves a paginated list of financial activities/campaigns with income, disbursements, and available balances.",
)
def list_activities(
    query: Optional[str] = Query(None, description="Search by activity name, code, purpose"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, COMPLETED, CANCELLED)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=1000, description="Items per page"),
    current_user: User = Depends(require_permission("Fund Collection", "View")),
    db: Session = Depends(get_db),
) -> FinancialActivityListResponse:
    return financial_activity_service.list_activities(
        db=db,
        query=query,
        status_filter=status,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{activity_id}",
    response_model=FinancialActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Financial Activity Detail",
    description="Retrieves detailed activity information including live available balance.",
)
def get_activity(
    activity_id: str,
    current_user: User = Depends(require_permission("Fund Collection", "View")),
    db: Session = Depends(get_db),
) -> FinancialActivityResponse:
    return financial_activity_service.get_activity(db=db, activity_id=activity_id)


@router.post(
    "",
    response_model=FinancialActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Financial Activity",
    description="Creates a new independent financial activity/campaign with dedicated ledger fund.",
)
def create_activity(
    data: FinancialActivityCreate,
    current_user: User = Depends(require_permission("Fund Collection", "Add")),
    db: Session = Depends(get_db),
) -> FinancialActivityResponse:
    return financial_activity_service.create_activity(
        db=db,
        data=data,
        current_user_id=current_user.id,
    )


@router.patch(
    "/{activity_id}",
    response_model=FinancialActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Financial Activity",
    description="Updates financial activity parameters, target budget, or status.",
)
def update_activity(
    activity_id: str,
    data: FinancialActivityUpdate,
    current_user: User = Depends(require_permission("Fund Collection", "Edit")),
    db: Session = Depends(get_db),
) -> FinancialActivityResponse:
    return financial_activity_service.update_activity(
        db=db,
        activity_id=activity_id,
        data=data,
        current_user_id=current_user.id,
    )


@router.post(
    "/{activity_id}/contribute",
    status_code=status.HTTP_201_CREATED,
    summary="Contribute / Income to Financial Activity",
    description="Receives income contribution from a Member or External Donor for this financial activity.",
)
def receive_activity_income(
    activity_id: str,
    data: FinancialActivityIncomeRequest,
    current_user: User = Depends(require_permission("Fund Collection", "Add")),
    db: Session = Depends(get_db),
) -> dict:
    return financial_activity_service.receive_income(
        db=db,
        activity_id=activity_id,
        data=data,
        current_user_id=current_user.id,
    )


@router.post(
    "/{activity_id}/disburse",
    status_code=status.HTTP_201_CREATED,
    summary="Disburse from Financial Activity to Beneficiary",
    description="Disburses funds to an active Beneficiary with atomic balance checks and double-entry transaction posting.",
)
def disburse_to_beneficiary(
    activity_id: str,
    data: FinancialActivityDisburseRequest,
    current_user: User = Depends(require_permission("Financial Support", "Add")),
    db: Session = Depends(get_db),
) -> dict:
    return financial_activity_service.disburse_to_beneficiary(
        db=db,
        activity_id=activity_id,
        data=data,
        current_user_id=current_user.id,
    )


@router.get(
    "/{activity_id}/ledger",
    response_model=FinancialActivityLedgerResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Financial Activity Ledger",
    description="Retrieves a complete chronological ledger of income and disbursements with calculated running balance.",
)
def get_activity_ledger(
    activity_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    current_user: User = Depends(require_permission("Fund Collection", "View")),
    db: Session = Depends(get_db),
) -> FinancialActivityLedgerResponse:
    return financial_activity_service.get_activity_ledger(
        db=db,
        activity_id=activity_id,
        page=page,
        page_size=page_size,
    )
