import uuid
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.donor import Donor
from app.models.ledger import LedgerTransaction
from app.models.auth import User
from app.rbac.dependencies import require_permission
from app.repositories import audit_repo
from pydantic import BaseModel

router = APIRouter(prefix="/donors", tags=["Donors Management"])


class DonorCreateRequest(BaseModel):
    fullName: str
    mobile: str
    address: Optional[str] = None
    nationalId: Optional[str] = None
    notes: Optional[str] = None


class DonorUpdateRequest(BaseModel):
    fullName: Optional[str] = None
    mobile: Optional[str] = None
    address: Optional[str] = None
    nationalId: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


@router.get("", response_model=List[Dict[str, Any]])
def list_donors(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("Donors", "View")),
):
    stmt = select(Donor).order_by(Donor.createdAt.desc())
    donors = db.scalars(stmt).all()
    results = []
    for d in donors:
        results.append({
            "id": d.id,
            "donorId": d.donorId,
            "fullName": d.fullName,
            "mobile": d.mobile,
            "address": d.address,
            "nationalId": d.nationalId,
            "notes": d.notes,
            "status": d.status,
            "createdAt": d.createdAt.isoformat() if d.createdAt else None,
            "updatedAt": d.updatedAt.isoformat() if d.updatedAt else None,
        })
    return results


@router.get("/{donor_id}", response_model=Dict[str, Any])
def get_donor(
    donor_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("Donors", "View")),
):
    d = db.get(Donor, donor_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor not found")

    return {
        "id": d.id,
        "donorId": d.donorId,
        "fullName": d.fullName,
        "mobile": d.mobile,
        "address": d.address,
        "nationalId": d.nationalId,
        "notes": d.notes,
        "status": d.status,
        "createdAt": d.createdAt.isoformat() if d.createdAt else None,
        "updatedAt": d.updatedAt.isoformat() if d.updatedAt else None,
        "documents": [],
    }


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_donor(
    data: DonorCreateRequest,
    current_user: User = Depends(require_permission("Donors", "Add")),
    db: Session = Depends(get_db),
):
    # generate donor ID
    count_stmt = select(func.count(Donor.id))
    cnt = db.scalar(count_stmt) or 0
    donor_id_str = f"DNR-{str(cnt + 1).zfill(4)}"

    d = Donor(
        donorId=donor_id_str,
        fullName=data.fullName.strip(),
        mobile=data.mobile.strip(),
        address=data.address.strip() if data.address else None,
        nationalId=data.nationalId.strip() if data.nationalId else None,
        notes=data.notes.strip() if data.notes else None,
        status="ACTIVE",
        createdBy=current_user.id,
    )
    db.add(d)
    audit_repo.log(
        db,
        action="CREATE",
        module="DONOR",
        user_id=current_user.id,
        remarks=f"Created donor {d.fullName} ({d.donorId})",
    )
    db.commit()
    db.refresh(d)
    return {"id": d.id, "donorId": d.donorId, "fullName": d.fullName}


@router.patch("/{donor_id}", response_model=Dict[str, Any])
def update_donor(
    donor_id: str,
    data: DonorUpdateRequest,
    current_user: User = Depends(require_permission("Donors", "Edit")),
    db: Session = Depends(get_db),
):
    d = db.get(Donor, donor_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor not found")

    if data.fullName is not None:
        d.fullName = data.fullName.strip()
    if data.mobile is not None:
        d.mobile = data.mobile.strip()
    if data.address is not None:
        d.address = data.address.strip() or None
    if data.nationalId is not None:
        d.nationalId = data.nationalId.strip() or None
    if data.notes is not None:
        d.notes = data.notes.strip() or None
    if data.status is not None:
        d.status = data.status

    audit_repo.log(
        db,
        action="UPDATE",
        module="DONOR",
        user_id=current_user.id,
        remarks=f"Updated donor {d.fullName} ({d.donorId})",
    )
    db.commit()
    db.refresh(d)
    return {"id": d.id, "donorId": d.donorId, "fullName": d.fullName}


@router.delete("/{donor_id}", response_model=Dict[str, bool])
def delete_donor(
    donor_id: str,
    current_user: User = Depends(require_permission("Donors", "Delete")),
    db: Session = Depends(get_db),
):
    d = db.get(Donor, donor_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor not found")

    # check if transactions exist
    stmt = select(LedgerTransaction).where(LedgerTransaction.donorId == donor_id)
    if db.scalars(stmt).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete donor with existing donations",
        )

    db.delete(d)
    audit_repo.log(
        db,
        action="DELETE",
        module="DONOR",
        user_id=current_user.id,
        remarks=f"Deleted donor {d.fullName} ({d.donorId})",
    )
    db.commit()
    return {"success": True}


@router.get("/{donor_id}/ledger", response_model=List[Dict[str, Any]])
def get_donor_ledger(
    donor_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("Donors", "View")),
):
    stmt = (
        select(LedgerTransaction)
        .where(LedgerTransaction.donorId == donor_id)
        .order_by(LedgerTransaction.transactionDate.desc())
    )
    txs = db.scalars(stmt).all()
    results = []
    for tx in txs:
        results.append({
            "id": tx.id,
            "transactionNumber": tx.transactionNumber,
            "date": tx.transactionDate.isoformat(),
            "amount": float(tx.amount),
            "paymentMethod": tx.paymentMethod,
            "type": tx.transactionType,
            "remarks": tx.remarks,
        })
    return results
