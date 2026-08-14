import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.ledger import LedgerTransaction, LedgerEntry
from app.models.member import Member
from app.models.donor import Donor
from app.models.fund import Fund
from app.models.organization import Group
from app.schemas.sadaqah import (
    SadaqahReceiveRequest,
    SadaqahResponse,
    SadaqahListResponse,
)
from app.repositories import (
    ledger_repo,
    member_repo,
    donor_repo,
    fund_repo,
    group_repo,
    audit_repo,
)


def format_sadaqah_response(tx: LedgerTransaction) -> SadaqahResponse:
    # Identify target credit entry
    credit_entry = next((e for e in tx.entries if e.isCredit), None)
    fund_id = credit_entry.fundId if credit_entry else ""
    fund_name = credit_entry.fund.name if (credit_entry and credit_entry.fund) else "General Foundation Fund"
    group_id = credit_entry.groupId if credit_entry else None
    group_name = credit_entry.groupName if credit_entry else None
    amount = credit_entry.amount if credit_entry else 0

    contributor_type = "MEMBER" if tx.memberId else "EXTERNAL"

    return SadaqahResponse(
        id=tx.id,
        date=tx.date,
        type=tx.type,
        contributor_type=contributor_type,
        member_id=tx.memberId,
        member_name=tx.member.fullName if tx.member else None,
        member_code=tx.member.memberId if tx.member else None,
        donor_id=tx.donorId,
        donor_name=tx.donor.fullName if tx.donor else None,
        donor_code=tx.donor.donorId if tx.donor else None,
        amount=amount,
        fund_id=fund_id,
        fund_name=fund_name,
        group_id=group_id,
        group_name=group_name,
        status=tx.status,
        notes=tx.notes,
        created_at=tx.createdAt,
    )


class SadaqahService:
    def receive_sadaqah(
        self,
        db: Session,
        data: SadaqahReceiveRequest,
        current_user_id: Optional[str] = None,
    ) -> SadaqahResponse:
        contributor_type = data.contributor_type.upper().strip()
        final_member_id: Optional[str] = None
        final_donor_id: Optional[str] = None

        # 1. Strict Contributor Validation (Member vs External Donor)
        if contributor_type == "MEMBER":
            if not data.member_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Member ID is required for contributor type 'MEMBER'.",
                )
            if data.donor_id or data.donor_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="External Donor ID/info must NOT be provided when contributor is a Member.",
                )
            member = member_repo.get_by_id(db, data.member_id)
            if not member:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Member with ID '{data.member_id}' not found.",
                )
            final_member_id = member.id
            ref_id = member.id

        elif contributor_type in ["EXTERNAL", "DONOR"]:
            if data.member_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Member ID must NOT be provided when contributor is an External Donor.",
                )
            if data.donor_info:
                # Check mobile uniqueness for donor
                existing_donor = donor_repo.get_by_mobile(db, data.donor_info.mobile)
                if existing_donor:
                    donor = existing_donor
                else:
                    new_donor_code = donor_repo.generate_next_donor_id(db)
                    donor = Donor(
                        donorId=new_donor_code,
                        fullName=data.donor_info.full_name.strip(),
                        mobile=data.donor_info.mobile.strip(),
                        address=data.donor_info.address,
                        nationalId=data.donor_info.national_id,
                        notes=data.donor_info.notes,
                        createdBy=current_user_id,
                    )
                    db.add(donor)
                    db.flush()
                final_donor_id = donor.id
            elif data.donor_id:
                donor = donor_repo.get_by_id(db, data.donor_id)
                if not donor:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Donor with ID '{data.donor_id}' not found.",
                    )
                final_donor_id = donor.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Either donor_id or donor_info is required for External Sadaqah.",
                )
            ref_id = final_donor_id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid contributor_type '{data.contributor_type}'. Must be 'MEMBER' or 'EXTERNAL'.",
            )

        # 2. Resolve Target Fund & General Fund
        general_fund = fund_repo.get_general_fund(db)
        target_group: Optional[Group] = None

        if data.fund_id:
            target_fund = fund_repo.get_by_id(db, data.fund_id)
            if not target_fund:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target fund '{data.fund_id}' not found.",
                )
            target_group = target_fund.group
        elif data.group_id:
            target_group = group_repo.get_by_id(db, data.group_id)
            if not target_group:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target group '{data.group_id}' not found.",
                )
            target_fund, general_fund = fund_repo.get_or_create_funds(db, data.group_id)
        else:
            target_fund = general_fund

        tx_date = data.date or datetime.datetime.now(datetime.timezone.utc)
        tx_type = "SADAQAH" if contributor_type == "MEMBER" else "DONATION"

        entries = [
            # Debit: General Asset / Cash pool
            {
                "fundId": general_fund.id,
                "isCredit": False,
                "amount": data.amount,
                "groupId": None,
                "groupCode": "HQ",
                "groupName": "General Pool",
            },
            # Credit: Target Dedicated Fund / Group Fund
            {
                "fundId": target_fund.id,
                "isCredit": True,
                "amount": data.amount,
                "groupId": target_group.id if target_group else None,
                "groupCode": target_group.code if target_group else "HQ",
                "groupName": target_group.name if target_group else "General Foundation Fund",
            },
        ]

        try:
            # 3. Create double-entry balanced transaction
            tx = ledger_repo.create_balanced_transaction(
                db=db,
                date=tx_date,
                type=tx_type,
                reference_id=ref_id,
                member_id=final_member_id,
                donor_id=final_donor_id,
                notes=data.notes or data.purpose or f"Received {tx_type}",
                created_by=current_user_id,
                entries=entries,
            )

            # 4. Audit Log
            audit_repo.log(
                db=db,
                action="RECEIVE",
                module="SADAQAH",
                user_id=current_user_id,
                reference_id=tx.id,
                remarks=f"Received {tx_type} of {data.amount} BDT for {target_fund.name}",
            )

            db.commit()
            db.refresh(tx)
            return format_sadaqah_response(tx)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Financial transaction failed: {str(e)}",
            )

    def list_sadaqah(
        self,
        db: Session,
        contributor_type: Optional[str] = None,
        member_id: Optional[str] = None,
        donor_id: Optional[str] = None,
        group_id: Optional[str] = None,
        fund_id: Optional[str] = None,
        query: Optional[str] = None,
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SadaqahListResponse:
        items, total_count, total_amount = ledger_repo.search_donations_and_paginate(
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
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        return SadaqahListResponse(
            items=[format_sadaqah_response(tx) for tx in items],
            total=total_count,
            total_amount=total_amount,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_sadaqah(self, db: Session, tx_id: str) -> SadaqahResponse:
        tx = ledger_repo.get_by_id(db, tx_id)
        if not tx or tx.type not in ["DONATION", "SADAQAH", "VOLUNTARY_SADAQAH"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sadaqah transaction with ID '{tx_id}' not found",
            )
        return format_sadaqah_response(tx)


sadaqah_service = SadaqahService()
