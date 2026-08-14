import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.campaign import Campaign, CampaignContribution, BeneficiaryPayment
from backend.app.models.donor import Donor
from backend.app.schemas.financial_activity import (
    FinancialActivityCreate,
    FinancialActivityUpdate,
    FinancialActivityResponse,
    FinancialActivityListResponse,
    FinancialActivityIncomeRequest,
    FinancialActivityDisburseRequest,
    FinancialActivityLedgerEntryItem,
    FinancialActivityLedgerResponse,
)
from backend.app.repositories import (
    campaign_repo,
    member_repo,
    donor_repo,
    beneficiary_repo,
    fund_repo,
    ledger_repo,
    audit_repo,
)


def format_activity_response(c: Campaign, db: Session) -> FinancialActivityResponse:
    income, expense, balance = campaign_repo.get_campaign_financials(db, c.id)
    return FinancialActivityResponse(
        id=c.id,
        activity_id=c.campaignId,
        name=c.name,
        purpose=c.purpose,
        description=c.description,
        target_amount=c.targetAmount,
        total_income=income,
        total_expense=expense,
        available_balance=balance,
        start_date=c.startDate,
        end_date=c.endDate,
        status=c.status,
        remarks=c.remarks,
        created_at=c.createdAt,
        updated_at=c.updatedAt,
    )


class FinancialActivityService:
    def list_activities(
        self,
        db: Session,
        query: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> FinancialActivityListResponse:
        items, total = campaign_repo.search_and_paginate(
            db=db,
            query=query,
            status_filter=status_filter,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return FinancialActivityListResponse(
            items=[format_activity_response(c, db) for c in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_activity(self, db: Session, activity_id: str) -> FinancialActivityResponse:
        campaign = campaign_repo.get_by_id(db, activity_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial Activity with ID '{activity_id}' not found",
            )
        return format_activity_response(campaign, db)

    def create_activity(
        self,
        db: Session,
        data: FinancialActivityCreate,
        current_user_id: Optional[str] = None,
    ) -> FinancialActivityResponse:
        activity_code = campaign_repo.generate_next_campaign_id(db)
        start_date = data.start_date or datetime.datetime.now(datetime.timezone.utc)

        campaign = Campaign(
            campaignId=activity_code,
            name=data.name.strip(),
            purpose=data.purpose.strip(),
            description=data.description,
            targetAmount=data.target_amount,
            startDate=start_date,
            endDate=data.end_date,
            status=data.status or "ACTIVE",
            remarks=data.remarks,
            createdBy=current_user_id,
        )
        db.add(campaign)
        db.flush()

        # Ensure dedicated fund exists
        campaign_repo.get_or_create_campaign_fund(db, campaign)

        audit_repo.log(
            db=db,
            action="CREATE",
            module="FUND_COLLECTION",
            user_id=current_user_id,
            reference_id=campaign.id,
            remarks=f"Created Financial Activity {campaign.campaignId} ({campaign.name})",
        )

        db.commit()
        db.refresh(campaign)
        return format_activity_response(campaign, db)

    def update_activity(
        self,
        db: Session,
        activity_id: str,
        data: FinancialActivityUpdate,
        current_user_id: Optional[str] = None,
    ) -> FinancialActivityResponse:
        campaign = campaign_repo.get_by_id(db, activity_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial Activity with ID '{activity_id}' not found",
            )

        if data.name is not None:
            campaign.name = data.name.strip()
        if data.purpose is not None:
            campaign.purpose = data.purpose.strip()
        if data.description is not None:
            campaign.description = data.description
        if data.target_amount is not None:
            campaign.targetAmount = data.target_amount
        if data.start_date is not None:
            campaign.startDate = data.start_date
        if data.end_date is not None:
            campaign.endDate = data.end_date
        if data.status is not None:
            campaign.status = data.status
        if data.remarks is not None:
            campaign.remarks = data.remarks

        campaign.updatedBy = current_user_id

        audit_repo.log(
            db=db,
            action="UPDATE",
            module="FUND_COLLECTION",
            user_id=current_user_id,
            reference_id=campaign.id,
            remarks=f"Updated Financial Activity {campaign.campaignId}",
        )

        db.commit()
        db.refresh(campaign)
        return format_activity_response(campaign, db)

    def receive_income(
        self,
        db: Session,
        activity_id: str,
        data: FinancialActivityIncomeRequest,
        current_user_id: Optional[str] = None,
    ) -> dict:
        campaign = campaign_repo.get_by_id(db, activity_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial Activity with ID '{activity_id}' not found",
            )
        if campaign.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot receive income for non-active activity (status: {campaign.status}).",
            )

        contributor_type = data.contributor_type.upper().strip()
        final_member_id: Optional[str] = None
        final_donor_id: Optional[str] = None

        if contributor_type == "MEMBER":
            if not data.member_id:
                raise HTTPException(status_code=400, detail="member_id is required for MEMBER contributor.")
            member = member_repo.get_by_id(db, data.member_id)
            if not member:
                raise HTTPException(status_code=404, detail=f"Member '{data.member_id}' not found.")
            final_member_id = member.id
            ref_id = member.id
        elif contributor_type in ["EXTERNAL", "DONOR"]:
            if data.donor_info:
                existing = donor_repo.get_by_mobile(db, data.donor_info.mobile)
                if existing:
                    donor = existing
                else:
                    new_code = donor_repo.generate_next_donor_id(db)
                    donor = Donor(
                        donorId=new_code,
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
                    raise HTTPException(status_code=404, detail=f"Donor '{data.donor_id}' not found.")
                final_donor_id = donor.id
            else:
                raise HTTPException(status_code=400, detail="Either donor_id or donor_info is required for External donor.")
            ref_id = final_donor_id
        else:
            raise HTTPException(status_code=400, detail="Invalid contributor_type. Must be 'MEMBER' or 'EXTERNAL'.")

        tx_date = data.date or datetime.datetime.now(datetime.timezone.utc)

        try:
            # 1. Dedicated campaign fund & general fund
            campaign_fund = campaign_repo.get_or_create_campaign_fund(db, campaign)
            general_fund = fund_repo.get_general_fund(db)

            # 2. Balanced double-entry
            entries = [
                {"fundId": general_fund.id, "isCredit": False, "amount": data.amount},
                {"fundId": campaign_fund.id, "isCredit": True, "amount": data.amount},
            ]

            tx = ledger_repo.create_balanced_transaction(
                db=db,
                date=tx_date,
                type="CAMPAIGN_CONTRIBUTION",
                reference_id=ref_id,
                member_id=final_member_id,
                donor_id=final_donor_id,
                notes=data.remarks or f"Contribution to {campaign.name}",
                created_by=current_user_id,
                entries=entries,
            )

            # 3. Record CampaignContribution
            cc = CampaignContribution(
                campaignId=campaign.id,
                memberId=final_member_id,
                donorId=final_donor_id,
                ledgerTransactionId=tx.id,
                amount=data.amount,
                date=tx_date,
                remarks=data.remarks,
                createdBy=current_user_id,
            )
            db.add(cc)
            db.flush()

            audit_repo.log(
                db=db,
                action="INCOME",
                module="FUND_COLLECTION",
                user_id=current_user_id,
                reference_id=cc.id,
                remarks=f"Received ৳{data.amount} for activity {campaign.campaignId}",
            )

            db.commit()
            return {
                "success": True,
                "campaign_id": campaign.id,
                "amount": data.amount,
                "ledger_transaction_id": tx.id,
                "message": f"Successfully received ৳{data.amount} for {campaign.name}",
            }
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Activity contribution failed: {str(e)}")

    def disburse_to_beneficiary(
        self,
        db: Session,
        activity_id: str,
        data: FinancialActivityDisburseRequest,
        current_user_id: Optional[str] = None,
    ) -> dict:
        campaign = campaign_repo.get_by_id(db, activity_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial Activity with ID '{activity_id}' not found",
            )
        if campaign.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot disburse from non-active activity (status: {campaign.status}).",
            )

        # Beneficiary validation
        beneficiary = beneficiary_repo.get_by_id(db, data.beneficiary_id)
        if not beneficiary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Beneficiary with ID '{data.beneficiary_id}' not found.",
            )
        if beneficiary.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot disburse to inactive beneficiary (status: {beneficiary.status}).",
            )

        # STRICT BALANCE CHECK: available_balance >= data.amount
        income, expense, balance = campaign_repo.get_campaign_financials(db, campaign.id)
        if data.amount > balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient available balance in activity {campaign.name}. Available: ৳{balance}, Requested disbursement: ৳{data.amount}.",
            )

        tx_date = data.date or datetime.datetime.now(datetime.timezone.utc)

        try:
            campaign_fund = campaign_repo.get_or_create_campaign_fund(db, campaign)
            general_fund = fund_repo.get_general_fund(db)

            # Balanced double-entry disbursement:
            # Debit: Campaign Fund (decrease equity/fund reserve)
            # Credit: General Cash pool (outflow to beneficiary)
            entries = [
                {"fundId": campaign_fund.id, "isCredit": False, "amount": data.amount},
                {"fundId": general_fund.id, "isCredit": True, "amount": data.amount},
            ]

            tx = ledger_repo.create_balanced_transaction(
                db=db,
                date=tx_date,
                type="BENEFICIARY_PAYMENT",
                reference_id=beneficiary.id,
                member_id=None,
                donor_id=None,
                notes=f"Disbursement to {beneficiary.fullName} for {data.reason}",
                created_by=current_user_id,
                entries=entries,
            )

            # Record BeneficiaryPayment
            bp = BeneficiaryPayment(
                campaignId=campaign.id,
                beneficiaryId=beneficiary.id,
                ledgerTransactionId=tx.id,
                amount=data.amount,
                date=tx_date,
                reason=data.reason.strip(),
                referenceNumber=data.reference_number,
                comments=data.comments,
                status="COMPLETED",
                createdBy=current_user_id,
            )
            db.add(bp)
            db.flush()

            audit_repo.log(
                db=db,
                action="DISBURSEMENT",
                module="FINANCIAL_SUPPORT",
                user_id=current_user_id,
                reference_id=bp.id,
                remarks=f"Disbursed ৳{data.amount} to {beneficiary.fullName} from {campaign.campaignId}",
            )

            db.commit()
            return {
                "success": True,
                "payment_id": bp.id,
                "amount": data.amount,
                "beneficiary_id": beneficiary.id,
                "beneficiary_name": beneficiary.fullName,
                "remaining_balance": balance - data.amount,
                "ledger_transaction_id": tx.id,
                "message": f"Successfully disbursed ৳{data.amount} to {beneficiary.fullName}",
            }
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Disbursement transaction failed: {str(e)}")

    def get_activity_ledger(
        self,
        db: Session,
        activity_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> FinancialActivityLedgerResponse:
        campaign = campaign_repo.get_by_id(db, activity_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial Activity with ID '{activity_id}' not found",
            )

        income, expense, balance = campaign_repo.get_campaign_financials(db, campaign.id)
        all_entries = campaign_repo.get_campaign_ledger_entries(db, campaign.id)

        total = len(all_entries)
        offset = (page - 1) * page_size
        paged_items = all_entries[offset : offset + page_size]

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        ledger_items = [
            FinancialActivityLedgerEntryItem(
                id=item["id"],
                date=item["date"],
                type=item["type"],
                amount=item["amount"],
                source_or_recipient=item["source_or_recipient"],
                reason=item["reason"],
                running_balance=item["running_balance"],
                reference_number=item["reference_number"],
                created_at=item["created_at"],
            )
            for item in paged_items
        ]

        return FinancialActivityLedgerResponse(
            activity_id=campaign.id,
            activity_code=campaign.campaignId,
            activity_name=campaign.name,
            current_balance=balance,
            total_income=income,
            total_disbursed=expense,
            items=ledger_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


financial_activity_service = FinancialActivityService()
