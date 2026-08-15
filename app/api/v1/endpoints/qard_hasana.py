from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.auth import User
from app.schemas.loan import (
    QardHasanaCreateRequest,
    QardHasanaUpdateRequest,
    QardHasanaResponse,
    QardHasanaListResponse,
    RepaymentCreateRequest,
    RepaymentResponse,
    QardHasanaLedgerResponse,
)
from app.services.loan_service import loan_service
from app.rbac.dependencies import require_permission

router = APIRouter(prefix="/qard-e-hasana", tags=["Qard-e-Hasana (কর্জে হাসানা / Interest-free Loans)"])


@router.get(
    "",
    response_model=QardHasanaListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Qard-e-Hasana Records",
    description="Retrieves a paginated list of Qard-e-Hasana records with status, member, and beneficiary filters.",
)
def list_qard_hasana(
    query: Optional[str] = Query(None, description="Search by loan number or purpose"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, PAID, DEFAULTED, CANCELLED)"),
    member_id: Optional[str] = Query(None, description="Filter by Member UUID"),
    beneficiary_id: Optional[str] = Query(None, description="Filter by Beneficiary UUID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=1000, description="Items per page"),
    current_user: User = Depends(require_permission("Loans", "View")),
    db: Session = Depends(get_db),
) -> QardHasanaListResponse:
    return loan_service.list_qard_hasana(
        db=db,
        query=query,
        status_filter=status,
        member_id=member_id,
        beneficiary_id=beneficiary_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{loan_id}",
    response_model=QardHasanaResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Qard-e-Hasana Detail",
    description="Retrieves full details of a specific Qard-e-Hasana record.",
)
def get_qard_hasana(
    loan_id: str,
    current_user: User = Depends(require_permission("Loans", "View")),
    db: Session = Depends(get_db),
) -> QardHasanaResponse:
    return loan_service.get_qard_hasana(db=db, loan_id=loan_id)


@router.post(
    "",
    response_model=QardHasanaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create / Disburse Qard-e-Hasana",
    description="Disburses a new interest-free Qard-e-Hasana to a Member or Beneficiary, allocating from Group Fund with double-entry accounting.",
)
def create_qard_hasana(
    data: QardHasanaCreateRequest,
    current_user: User = Depends(require_permission("Loans", "Add")),
    db: Session = Depends(get_db),
) -> QardHasanaResponse:
    return loan_service.create_qard_hasana(
        db=db,
        data=data,
        current_user_id=current_user.id,
    )


@router.patch(
    "/{loan_id}",
    response_model=QardHasanaResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Qard-e-Hasana",
    description="Updates Qard-e-Hasana purpose, installment plan, or remarks.",
)
def update_qard_hasana(
    loan_id: str,
    data: QardHasanaUpdateRequest,
    current_user: User = Depends(require_permission("Loans", "Edit")),
    db: Session = Depends(get_db),
) -> QardHasanaResponse:
    return loan_service.update_qard_hasana(
        db=db,
        loan_id=loan_id,
        data=data,
        current_user_id=current_user.id,
    )


@router.post(
    "/{loan_id}/repayments",
    response_model=RepaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Qard-e-Hasana Repayment",
    description="Records repayment installment, atomically updating outstanding balance, status, and ledger transactions.",
)
def repay_qard_hasana(
    loan_id: str,
    data: RepaymentCreateRequest,
    current_user: User = Depends(require_permission("Loans", "Manage")),
    db: Session = Depends(get_db),
) -> RepaymentResponse:
    return loan_service.repay_qard_hasana(
        db=db,
        loan_id=loan_id,
        data=data,
        current_user_id=current_user.id,
    )


@router.get(
    "/{loan_id}/ledger",
    response_model=QardHasanaLedgerResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Qard-e-Hasana Ledger",
    description="Retrieves a complete chronological ledger of disbursement and all repayments with calculated running outstanding balance.",
)
def get_qard_hasana_ledger(
    loan_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    current_user: User = Depends(require_permission("Loans", "View")),
    db: Session = Depends(get_db),
) -> QardHasanaLedgerResponse:
    return loan_service.get_qard_hasana_ledger(
        db=db,
        loan_id=loan_id,
        page=page,
        page_size=page_size,
    )
