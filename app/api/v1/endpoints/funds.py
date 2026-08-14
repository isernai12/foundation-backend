from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.auth import User
from backend.app.schemas.fund import (
    FundCreateRequest,
    FundUpdateRequest,
    FundResponse,
    FundListResponse,
)
from backend.app.services.fund_service import fund_service
from backend.app.rbac.dependencies import require_permission

router = APIRouter(prefix="/funds", tags=["Funds"])


@router.get(
    "",
    response_model=FundListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Funds",
    description="Retrieves a paginated list of central and dedicated group funds with current balance.",
)
def list_funds(
    query: Optional[str] = Query(None, description="Search by fund name or description"),
    group_id: Optional[str] = Query(None, description="Filter by group UUID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_permission("Fund Collection", "View")),
    db: Session = Depends(get_db),
) -> FundListResponse:
    return fund_service.list_funds(
        db=db,
        query=query,
        group_id=group_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{fund_id}",
    response_model=FundResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Fund Detail",
    description="Retrieves fund details and live financial balance.",
)
def get_fund(
    fund_id: str,
    current_user: User = Depends(require_permission("Fund Collection", "View")),
    db: Session = Depends(get_db),
) -> FundResponse:
    return fund_service.get_fund(db=db, fund_id=fund_id)


@router.post(
    "",
    response_model=FundResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Fund",
    description="Creates a new dedicated or campaign fund.",
)
def create_fund(
    data: FundCreateRequest,
    current_user: User = Depends(require_permission("Fund Collection", "Add")),
    db: Session = Depends(get_db),
) -> FundResponse:
    return fund_service.create_fund(db=db, data=data, current_user_id=current_user.id)


@router.patch(
    "/{fund_id}",
    response_model=FundResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Fund",
    description="Updates fund name, description, or group association.",
)
def update_fund(
    fund_id: str,
    data: FundUpdateRequest,
    current_user: User = Depends(require_permission("Fund Collection", "Edit")),
    db: Session = Depends(get_db),
) -> FundResponse:
    return fund_service.update_fund(
        db=db,
        fund_id=fund_id,
        data=data,
        current_user_id=current_user.id,
    )
