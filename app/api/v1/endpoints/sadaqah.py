import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.auth import User
from app.schemas.sadaqah import (
    SadaqahReceiveRequest,
    SadaqahResponse,
    SadaqahListResponse,
)
from app.services.sadaqah_service import sadaqah_service
from app.rbac.dependencies import require_permission

router = APIRouter(prefix="/sadaqah", tags=["Donation / Sadaqah"])


@router.post(
    "",
    response_model=SadaqahResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Receive Donation / Sadaqah",
    description="Receives voluntary Sadaqah from a Foundation Member or External Donor, allocating it to the designated Fund/Group with double-entry balanced ledger posting.",
)
def receive_sadaqah(
    data: SadaqahReceiveRequest,
    current_user: User = Depends(require_permission("Donors", "Receive Installment")),
    db: Session = Depends(get_db),
) -> SadaqahResponse:
    return sadaqah_service.receive_sadaqah(
        db=db,
        data=data,
        current_user_id=current_user.id,
    )


@router.get(
    "",
    response_model=SadaqahListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Received Sadaqah",
    description="Retrieves a paginated list of Sadaqah transactions with contributor type, member, donor, date, and fund filters.",
)
def list_sadaqah(
    contributor_type: Optional[str] = Query(None, description="Filter by contributor type (MEMBER, EXTERNAL)"),
    member_id: Optional[str] = Query(None, description="Filter by Member UUID"),
    donor_id: Optional[str] = Query(None, description="Filter by Donor UUID"),
    group_id: Optional[str] = Query(None, description="Filter by Group UUID"),
    fund_id: Optional[str] = Query(None, description="Filter by Fund UUID"),
    query: Optional[str] = Query(None, description="Search by contributor name or remarks"),
    start_date: Optional[datetime.datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime.datetime] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_permission("Donors", "View")),
    db: Session = Depends(get_db),
) -> SadaqahListResponse:
    return sadaqah_service.list_sadaqah(
        db=db,
        contributor_type=contributor_type,
        member_id=member_id,
        donor_id=donor_id,
        group_id=group_id,
        fund_id=fund_id,
        query=query,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{sadaqah_id}",
    response_model=SadaqahResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Sadaqah Transaction Detail",
    description="Retrieves full details of a specific Sadaqah / Donation transaction.",
)
def get_sadaqah(
    sadaqah_id: str,
    current_user: User = Depends(require_permission("Donors", "View")),
    db: Session = Depends(get_db),
) -> SadaqahResponse:
    return sadaqah_service.get_sadaqah(db=db, tx_id=sadaqah_id)
