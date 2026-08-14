from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.auth import User
from backend.app.schemas.beneficiary import (
    BeneficiaryCreateRequest,
    BeneficiaryUpdateRequest,
    BeneficiaryResponse,
    BeneficiaryListResponse,
)
from backend.app.services.beneficiary_service import beneficiary_service
from backend.app.rbac.dependencies import require_permission

router = APIRouter(prefix="/beneficiaries", tags=["Beneficiaries"])


@router.get(
    "",
    response_model=BeneficiaryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Beneficiaries",
    description="Retrieves a paginated list of registered beneficiaries with search and status filters.",
)
def list_beneficiaries(
    query: Optional[str] = Query(None, description="Search by name, code, mobile, NID"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, INACTIVE)"),
    member_id: Optional[str] = Query(None, description="Filter by linked Member UUID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_permission("Beneficiaries", "View")),
    db: Session = Depends(get_db),
) -> BeneficiaryListResponse:
    return beneficiary_service.list_beneficiaries(
        db=db,
        query=query,
        status_filter=status,
        member_id=member_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{beneficiary_id}",
    response_model=BeneficiaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Beneficiary Detail",
    description="Retrieves details of a specific beneficiary.",
)
def get_beneficiary(
    beneficiary_id: str,
    current_user: User = Depends(require_permission("Beneficiaries", "View")),
    db: Session = Depends(get_db),
) -> BeneficiaryResponse:
    return beneficiary_service.get_beneficiary(db=db, beneficiary_id=beneficiary_id)


@router.post(
    "",
    response_model=BeneficiaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Beneficiary",
    description="Registers a new beneficiary entity with sequential BEN-XXXX ID.",
)
def create_beneficiary(
    data: BeneficiaryCreateRequest,
    current_user: User = Depends(require_permission("Beneficiaries", "Add")),
    db: Session = Depends(get_db),
) -> BeneficiaryResponse:
    return beneficiary_service.create_beneficiary(
        db=db,
        data=data,
        current_user_id=current_user.id,
    )


@router.patch(
    "/{beneficiary_id}",
    response_model=BeneficiaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Beneficiary",
    description="Updates beneficiary profile, address, or assistance information.",
)
def update_beneficiary(
    beneficiary_id: str,
    data: BeneficiaryUpdateRequest,
    current_user: User = Depends(require_permission("Beneficiaries", "Edit")),
    db: Session = Depends(get_db),
) -> BeneficiaryResponse:
    return beneficiary_service.update_beneficiary(
        db=db,
        beneficiary_id=beneficiary_id,
        data=data,
        current_user_id=current_user.id,
    )
