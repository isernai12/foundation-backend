import re
import datetime
from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session, joinedload
from backend.app.models.campaign import Campaign, CampaignContribution, BeneficiaryPayment
from backend.app.models.fund import Fund
from backend.app.models.ledger import LedgerTransaction, LedgerEntry
from backend.app.models.beneficiary import Beneficiary
from backend.app.models.member import Member
from backend.app.models.donor import Donor
from backend.app.repositories.base import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    def __init__(self):
        super().__init__(Campaign)

    def get_by_id(self, db: Session, campaign_id: str) -> Optional[Campaign]:
        stmt = (
            select(Campaign)
            .where(Campaign.id == campaign_id)
            .options(
                joinedload(Campaign.contributions),
                joinedload(Campaign.beneficiaryPayments),
            )
        )
        return db.scalars(stmt).unique().first()

    def get_by_code(self, db: Session, code: str) -> Optional[Campaign]:
        stmt = select(Campaign).where(Campaign.campaignId == code.strip())
        return db.scalars(stmt).first()

    def generate_next_campaign_id(self, db: Session) -> str:
        stmt = select(Campaign.campaignId)
        all_ids = db.scalars(stmt).all()

        max_num = 0
        existing_set = set()

        for cid in all_ids:
            if not cid:
                continue
            existing_set.add(cid)
            match = re.search(r"(\d+)$", cid)
            if match:
                try:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

        next_num = max_num + 1
        candidate = f"CMP-{next_num:04d}"
        while candidate in existing_set:
            next_num += 1
            candidate = f"CMP-{next_num:04d}"

        return candidate

    def get_or_create_campaign_fund(self, db: Session, campaign: Campaign) -> Fund:
        fund_name = f"Campaign: {campaign.name}"
        stmt = select(Fund).where(Fund.name == fund_name)
        fund = db.scalars(stmt).first()
        if not fund:
            fund = Fund(
                name=fund_name,
                description=f"Automated dedicated fund for campaign {campaign.campaignId} ({campaign.name})",
            )
            db.add(fund)
            db.flush()
        return fund

    def get_campaign_financials(self, db: Session, campaign_id: str) -> Tuple[int, int, int]:
        """
        Calculates total income, total disbursements (expense), and available balance for an activity.
        """
        # Income from CampaignContribution
        stmt_income = (
            select(func.coalesce(func.sum(CampaignContribution.amount), 0))
            .where(CampaignContribution.campaignId == campaign_id)
        )
        income = db.scalar(stmt_income) or 0

        # Expense from BeneficiaryPayment
        stmt_expense = (
            select(func.coalesce(func.sum(BeneficiaryPayment.amount), 0))
            .where(and_(BeneficiaryPayment.campaignId == campaign_id, BeneficiaryPayment.status == "COMPLETED"))
        )
        expense = db.scalar(stmt_expense) or 0

        balance = income - expense
        return int(income), int(expense), int(balance)

    def search_and_paginate(
        self,
        db: Session,
        query: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Campaign], int]:
        stmt = select(Campaign)
        filters = []

        if status_filter:
            filters.append(Campaign.status == status_filter)

        if query and query.strip():
            search = f"%{query.strip()}%"
            filters.append(
                or_(
                    Campaign.name.ilike(search),
                    Campaign.campaignId.ilike(search),
                    Campaign.purpose.ilike(search),
                    Campaign.description.ilike(search),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        stmt = stmt.order_by(Campaign.createdAt.desc())
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        items = list(db.scalars(stmt).unique().all())
        return items, total

    def get_campaign_ledger_entries(
        self,
        db: Session,
        campaign_id: str,
    ) -> List[dict]:
        """
        Gathers chronological income and disbursement transactions for the activity ledger.
        """
        # 1. Income entries
        stmt_inc = (
            select(CampaignContribution)
            .where(CampaignContribution.campaignId == campaign_id)
            .options(
                joinedload(CampaignContribution.member),
                joinedload(CampaignContribution.donor),
            )
            .order_by(CampaignContribution.date.asc(), CampaignContribution.createdAt.asc())
        )
        contributions = db.scalars(stmt_inc).unique().all()

        # 2. Disbursement entries
        stmt_exp = (
            select(BeneficiaryPayment)
            .where(BeneficiaryPayment.campaignId == campaign_id)
            .options(joinedload(BeneficiaryPayment.beneficiary))
            .order_by(BeneficiaryPayment.date.asc(), BeneficiaryPayment.createdAt.asc())
        )
        payments = db.scalars(stmt_exp).unique().all()

        # Merge and sort chronologically
        merged = []
        for c in contributions:
            source = "Anonymous"
            if c.member:
                source = f"Member: {c.member.fullName} ({c.member.memberId})"
            elif c.donor:
                source = f"Donor: {c.donor.fullName} ({c.donor.donorId})"

            merged.append({
                "id": c.id,
                "date": c.date,
                "created_at": c.createdAt,
                "type": "INCOME",
                "amount": c.amount,
                "source_or_recipient": source,
                "reason": c.remarks or "Campaign Contribution",
                "reference_number": None,
            })

        for p in payments:
            recipient = f"Beneficiary: {p.beneficiary.fullName} ({p.beneficiary.beneficiaryId})" if p.beneficiary else "Beneficiary"
            merged.append({
                "id": p.id,
                "date": p.date,
                "created_at": p.createdAt,
                "type": "DISBURSEMENT",
                "amount": p.amount,
                "source_or_recipient": recipient,
                "reason": p.reason,
                "reference_number": p.referenceNumber,
            })

        merged.sort(key=lambda x: (x["date"], x["created_at"]))

        # Calculate running balance
        running = 0
        for item in merged:
            if item["type"] == "INCOME":
                running += item["amount"]
            else:
                running -= item["amount"]
            item["running_balance"] = running

        return merged


campaign_repo = CampaignRepository()
