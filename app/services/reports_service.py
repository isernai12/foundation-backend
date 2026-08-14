import datetime
from typing import List
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from backend.app.models.contribution import ContributionPayment
from backend.app.models.ledger import LedgerTransaction, LedgerEntry
from backend.app.models.campaign import CampaignContribution, BeneficiaryPayment
from backend.app.models.loan import Loan, LoanRepayment
from backend.app.models.organization import Group
from backend.app.schemas.reports import (
    FinancialDomainSummary,
    GroupFinancialSummaryItem,
    FinancialReportSummaryResponse,
)
from backend.app.repositories import group_repo, fund_repo


class ReportsService:
    def get_financial_summary(self, db: Session) -> FinancialReportSummaryResponse:
        # 1. Total Monthly Membership Dues
        stmt_dues = select(func.coalesce(func.sum(ContributionPayment.amount), 0))
        total_dues = db.scalar(stmt_dues) or 0

        # 2. Total Sadaqah / Donations
        stmt_sadaqah = (
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .join(LedgerTransaction, LedgerTransaction.id == LedgerEntry.transactionId)
            .where(
                and_(
                    LedgerTransaction.type.in_(["DONATION", "SADAQAH"]),
                    LedgerEntry.isCredit == True,
                )
            )
        )
        total_sadaqah = db.scalar(stmt_sadaqah) or 0

        # 3. Financial Activities Income, Expense, Balance
        stmt_act_inc = select(func.coalesce(func.sum(CampaignContribution.amount), 0))
        act_income = db.scalar(stmt_act_inc) or 0

        stmt_act_exp = select(func.coalesce(func.sum(BeneficiaryPayment.amount), 0)).where(
            BeneficiaryPayment.status == "COMPLETED"
        )
        act_expense = db.scalar(stmt_act_exp) or 0
        act_balance = act_income - act_expense

        # 4. Qard-e-Hasana Disbursed, Repaid, Outstanding
        stmt_loan_disb = select(func.coalesce(func.sum(Loan.amount), 0))
        loan_disbursed = db.scalar(stmt_loan_disb) or 0

        stmt_loan_rep = select(func.coalesce(func.sum(LoanRepayment.amount), 0)).where(
            LoanRepayment.status == "COMPLETED"
        )
        loan_repaid = db.scalar(stmt_loan_rep) or 0
        loan_outstanding = max(0, loan_disbursed - loan_repaid)

        # Total liquid funds = Dues + Sadaqah + Activity Balance + Loan Repaid - Loan Disbursed
        total_liquid = total_dues + total_sadaqah + act_balance + loan_repaid - loan_disbursed

        overall = FinancialDomainSummary(
            monthly_dues_total=int(total_dues),
            sadaqah_total=int(total_sadaqah),
            financial_activities_income=int(act_income),
            financial_activities_disbursed=int(act_expense),
            financial_activities_balance=int(act_balance),
            qard_hasana_disbursed=int(loan_disbursed),
            qard_hasana_repaid=int(loan_repaid),
            qard_hasana_outstanding=int(loan_outstanding),
            total_liquid_funds=int(total_liquid),
        )

        # 5. Group by Group Financial Summary
        stmt_groups = select(Group).order_by(Group.isFoundationGroup.desc(), Group.name.asc())
        groups = db.scalars(stmt_groups).all()

        group_items = []
        for g in groups:
            member_count = group_repo.get_member_count(db, g.id)
            current_bal = group_repo.get_group_balance(db, g.id)

            # Dues collected for this group's members
            stmt_grp_dues = (
                select(func.coalesce(func.sum(ContributionPayment.amount), 0))
                .join(ContributionPayment.monthlyContribution)
                .join(ContributionPayment.monthlyContribution.property.mapper.class_.member)
                .where(ContributionPayment.monthlyContribution.property.mapper.class_.member.property.mapper.class_.groupId == g.id)
            )
            # Safe calculation via LedgerEntry
            stmt_g_credit = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                and_(
                    LedgerEntry.groupId == g.id,
                    LedgerEntry.isCredit == True,
                )
            )
            grp_sadaqah = (
                db.scalar(
                    select(func.coalesce(func.sum(LedgerEntry.amount), 0))
                    .join(LedgerTransaction, LedgerTransaction.id == LedgerEntry.transactionId)
                    .where(
                        and_(
                            LedgerEntry.groupId == g.id,
                            LedgerEntry.isCredit == True,
                            LedgerTransaction.type.in_(["DONATION", "SADAQAH"]),
                        )
                    )
                )
                or 0
            )

            grp_loan_disb = (
                db.scalar(
                    select(func.coalesce(func.sum(Loan.amount), 0))
                    .join(Loan.member)
                    .where(Loan.member.property.mapper.class_.groupId == g.id)
                )
                or 0
            )

            grp_loan_rep = (
                db.scalar(
                    select(func.coalesce(func.sum(LoanRepayment.amount), 0))
                    .join(LoanRepayment.loan)
                    .join(Loan.member)
                    .where(Loan.member.property.mapper.class_.groupId == g.id)
                )
                or 0
            )

            group_items.append(
                GroupFinancialSummaryItem(
                    group_id=g.id,
                    group_code=g.code,
                    group_name=g.name,
                    is_foundation_group=g.isFoundationGroup,
                    member_count=member_count,
                    dues_collected=int(current_bal),
                    sadaqah_collected=int(grp_sadaqah),
                    qard_hasana_disbursed=int(grp_loan_disb),
                    qard_hasana_repaid=int(grp_loan_rep),
                    current_balance=int(current_bal),
                )
            )

        return FinancialReportSummaryResponse(
            generated_at=datetime.datetime.now(datetime.timezone.utc),
            overall=overall,
            groups=group_items,
        )


reports_service = ReportsService()
