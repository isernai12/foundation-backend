import datetime
from typing import List
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from app.models.contribution import ContributionPayment
from app.models.ledger import LedgerTransaction, LedgerEntry
from app.models.campaign import CampaignContribution, BeneficiaryPayment
from app.models.loan import Loan, LoanRepayment
from app.models.organization import Group
from app.schemas.reports import (
    FinancialDomainSummary,
    GroupFinancialSummaryItem,
    FinancialReportSummaryResponse,
    DashboardStatsResponse,
)
from app.repositories import group_repo, fund_repo


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

    def get_dashboard_stats(self, db: Session) -> DashboardStatsResponse:
        from app.models.membership import Member
        from app.models.organization import Group
        from app.models.beneficiary import Beneficiary
        from app.models.grant import Grant
        from app.models.loan import Loan, LoanRepayment
        from app.models.contribution import MonthlyContribution
        from app.schemas.reports import DashboardStatsResponse, GroupDistributionItem, MonthlyChartItem

        # 1. Member counts
        stmt_active = select(func.count(Member.id)).where(Member.status == "ACTIVE")
        stmt_total_m = select(func.count(Member.id))
        total_members = db.scalar(stmt_total_m) or 0
        active_members = db.scalar(stmt_active) or 0
        inactive_members = max(0, total_members - active_members)

        # 2. Counts
        total_groups = db.scalar(select(func.count(Group.id))) or 0
        total_beneficiaries = db.scalar(select(func.count(Beneficiary.id))) or 0
        total_grants = db.scalar(select(func.count(Grant.id))) or 0
        total_active_loans = db.scalar(select(func.count(Loan.id)).where(Loan.status == "ACTIVE")) or 0

        # 3. Loan totals
        total_loan_amount = db.scalar(
            select(func.coalesce(func.sum(Loan.amount), 0)).where(Loan.status.in_(["ACTIVE", "DEFAULTED"]))
        ) or 0
        total_repaid = db.scalar(
            select(func.coalesce(func.sum(LoanRepayment.amount), 0))
            .join(LoanRepayment.loan)
            .where(Loan.status.in_(["ACTIVE", "DEFAULTED"]))
        ) or 0
        outstanding_loan_amount = max(0, total_loan_amount - total_repaid)

        # 4. Total contributions
        total_contrib = db.scalar(
            select(func.coalesce(func.sum(MonthlyContribution.expectedAmount), 0)).where(
                MonthlyContribution.status == "PAID"
            )
        ) or 0

        # 5. Financial summaries & group balances
        groups = db.scalars(select(Group).order_by(Group.isFoundationGroup.desc(), Group.name.asc())).all()
        group_distribution = []
        total_group_funds = 0
        current_cash_balance = 0

        for g in groups:
            bal = group_repo.get_group_balance(db, g.id)
            if g.isFoundationGroup:
                current_cash_balance = bal
            else:
                total_group_funds += bal
                group_distribution.append(GroupDistributionItem(name=g.name, value=bal))

        # 6. Monthly chart data (last 6 months)
        now = datetime.datetime.now(datetime.timezone.utc)
        six_months_ago = now - datetime.timedelta(days=180)

        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        month_map = {}
        for i in range(5, -1, -1):
            d = now - datetime.timedelta(days=i * 30)
            m_name = month_names[d.month - 1]
            month_map[m_name] = MonthlyChartItem(month=m_name, contributions=0, loans=0, grants=0)

        contribs = db.execute(
            select(MonthlyContribution.expectedAmount, MonthlyContribution.createdAt).where(
                and_(MonthlyContribution.status == "PAID", MonthlyContribution.createdAt >= six_months_ago)
            )
        ).all()
        for c_amount, c_date in contribs:
            if c_date:
                m_name = month_names[c_date.month - 1]
                if m_name in month_map:
                    month_map[m_name].contributions += c_amount or 0

        loans = db.execute(
            select(Loan.amount, Loan.createdAt).where(Loan.createdAt >= six_months_ago)
        ).all()
        for l_amount, l_date in loans:
            if l_date:
                m_name = month_names[l_date.month - 1]
                if m_name in month_map:
                    month_map[m_name].loans += l_amount or 0

        grants = db.execute(
            select(Grant.amount, Grant.createdAt).where(Grant.createdAt >= six_months_ago)
        ).all()
        for g_amount, g_date in grants:
            if g_date:
                m_name = month_names[g_date.month - 1]
                if m_name in month_map:
                    month_map[m_name].grants += g_amount or 0

        return DashboardStatsResponse(
            totalMembers=total_members,
            activeMembers=active_members,
            inactiveMembers=inactive_members,
            totalGroups=total_groups,
            foundationTotalFund=current_cash_balance,
            totalGroupFunds=total_group_funds,
            currentCashBalance=current_cash_balance,
            totalContributions=total_contrib,
            totalActiveLoans=total_active_loans,
            outstandingLoanAmount=outstanding_loan_amount,
            totalGrants=total_grants,
            totalBeneficiaries=total_beneficiaries,
            groupFundDistribution=group_distribution,
            monthlyChartData=list(month_map.values()),
        )


reports_service = ReportsService()
