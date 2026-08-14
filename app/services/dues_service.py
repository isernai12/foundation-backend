import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.contribution import MonthlyContribution, ContributionPayment
from backend.app.models.member import Member
from backend.app.models.ledger import LedgerTransaction
from backend.app.schemas.dues import (
    SingleDuePayRequest,
    MultiMonthDuePayRequest,
    PaidMonthDetail,
    DuePaymentResponse,
    MemberDuesSummaryResponse,
    MemberDuesLedgerItem,
    MemberDuesLedgerResponse,
)
from backend.app.repositories import (
    contribution_repo,
    member_repo,
    fund_repo,
    ledger_repo,
    settings_repo,
    audit_repo,
)


def generate_month_range(from_month: int, from_year: int, to_month: int, to_year: int) -> List[Tuple[int, int]]:
    """
    Generates a list of (month, year) tuples covering the range across year boundaries.
    """
    if from_year > to_year or (from_year == to_year and from_month > to_month):
        raise ValueError("Start month/year must be prior or equal to end month/year.")

    results = []
    cur_y, cur_m = from_year, from_month

    while cur_y < to_year or (cur_y == to_year and cur_m <= to_month):
        results.append((cur_m, cur_y))
        cur_m += 1
        if cur_m > 12:
            cur_m = 1
            cur_y += 1

    return results


class DuesService:
    def pay_single_month(
        self,
        db: Session,
        data: SingleDuePayRequest,
        current_user_id: Optional[str] = None,
    ) -> DuePaymentResponse:
        member = member_repo.get_by_id(db, data.member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member with ID '{data.member_id}' not found",
            )

        # Check duplicate payment if not additional
        if not data.is_additional:
            existing = contribution_repo.get_contribution(
                db=db,
                member_id=data.member_id,
                month=data.month,
                year=data.year,
                is_additional=False,
            )
            if existing and existing.status == "PAID":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Monthly contribution for {data.month}/{data.year} is already fully paid. Use 'is_additional=True' for extra voluntary dues.",
                )

        # Dynamic monthly fee from Settings if not specified
        default_fee = settings_repo.get_monthly_membership_fee(db)
        amount = data.amount if data.amount is not None else default_fee
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment amount must be strictly positive.",
            )

        pay_date = data.payment_date or datetime.datetime.now(datetime.timezone.utc)

        try:
            # 1. Resolve Funds
            group_fund, general_fund = fund_repo.get_or_create_funds(db, member.groupId)

            # 2. Balanced Ledger Transaction
            entries = [
                {"fundId": general_fund.id, "isCredit": False, "amount": amount},  # Debit cash
                {
                    "fundId": group_fund.id,
                    "isCredit": True,
                    "amount": amount,
                    "groupId": member.groupId,
                    "groupCode": member.group.code if member.group else None,
                    "groupName": member.group.name if member.group else None,
                },  # Credit group fund
            ]

            tx = ledger_repo.create_balanced_transaction(
                db=db,
                date=pay_date,
                type="CONTRIBUTION",
                reference_id=data.reference_number,
                member_id=member.id,
                donor_id=None,
                notes=data.notes or f"Monthly Dues for {data.month}/{data.year}",
                created_by=current_user_id,
                entries=entries,
            )

            # 3. Create or update MonthlyContribution
            contribution = contribution_repo.get_contribution(
                db=db,
                member_id=data.member_id,
                month=data.month,
                year=data.year,
                is_additional=data.is_additional,
            )
            if contribution:
                contribution.status = "PAID"
                contribution.expectedAmount = amount
                contribution.updatedBy = current_user_id
            else:
                contribution = MonthlyContribution(
                    memberId=data.member_id,
                    month=data.month,
                    year=data.year,
                    expectedAmount=amount,
                    isAdditional=data.is_additional,
                    status="PAID",
                    createdBy=current_user_id,
                )
                db.add(contribution)
                db.flush()

            # 4. Record ContributionPayment
            payment = ContributionPayment(
                monthlyContributionId=contribution.id,
                ledgerTransactionId=tx.id,
                amount=amount,
                paymentDate=pay_date,
                paymentMethod=data.payment_method,
                referenceNumber=data.reference_number,
                notes=data.notes,
                createdBy=current_user_id,
            )
            db.add(payment)
            db.flush()

            # 5. Update paidUntil state on Member
            paid_m, paid_y = contribution_repo.update_member_paid_until(db, member.id)

            # 6. Audit Log
            audit_repo.log(
                db=db,
                action="PAYMENT",
                module="MEMBERS",
                user_id=current_user_id,
                reference_id=payment.id,
                remarks=f"Collected dues for {member.memberId} ({data.month}/{data.year}) - ৳{amount}",
            )

            db.commit()
            db.refresh(tx)

            return DuePaymentResponse(
                success=True,
                member_id=member.id,
                total_amount_paid=amount,
                months_paid=[
                    PaidMonthDetail(
                        month=data.month,
                        year=data.year,
                        amount=amount,
                        monthly_contribution_id=contribution.id,
                    )
                ],
                paid_until_month=paid_m,
                paid_until_year=paid_y,
                ledger_transaction_id=tx.id,
                message=f"Successfully collected dues for {data.month}/{data.year}",
            )
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Dues collection transaction failed: {str(e)}",
            )

    def pay_multi_month_advance(
        self,
        db: Session,
        data: MultiMonthDuePayRequest,
        current_user_id: Optional[str] = None,
    ) -> DuePaymentResponse:
        member = member_repo.get_by_id(db, data.member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member with ID '{data.member_id}' not found",
            )

        try:
            month_range = generate_month_range(
                from_month=data.from_month,
                from_year=data.from_year,
                to_month=data.to_month,
                to_year=data.to_year,
            )
        except ValueError as ve:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

        # Check existing contributions in range
        unpaid_months = []
        for m, y in month_range:
            existing = contribution_repo.get_contribution(db, member.id, m, y, is_additional=False)
            if not existing or existing.status != "PAID":
                unpaid_months.append((m, y, existing))

        if not unpaid_months:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"All months in range {data.from_month}/{data.from_year} to {data.to_month}/{data.to_year} are already fully paid.",
            )

        fee_per_month = (
            data.amount_per_month
            if data.amount_per_month is not None
            else settings_repo.get_monthly_membership_fee(db)
        )
        total_amount = fee_per_month * len(unpaid_months)
        pay_date = data.payment_date or datetime.datetime.now(datetime.timezone.utc)

        try:
            # 1. Resolve Funds
            group_fund, general_fund = fund_repo.get_or_create_funds(db, member.groupId)

            paid_details = []
            last_tx_id = ""

            # 2. Process each month with individual balanced ledger transaction (preserving 1-to-1 constraint)
            for m, y, existing in unpaid_months:
                if existing:
                    existing.status = "PAID"
                    existing.expectedAmount = fee_per_month
                    existing.updatedBy = current_user_id
                    contribution = existing
                else:
                    contribution = MonthlyContribution(
                        memberId=member.id,
                        month=m,
                        year=y,
                        expectedAmount=fee_per_month,
                        isAdditional=False,
                        status="PAID",
                        createdBy=current_user_id,
                    )
                    db.add(contribution)
                    db.flush()

                # Balanced Ledger Transaction for this month
                entries = [
                    {"fundId": general_fund.id, "isCredit": False, "amount": fee_per_month},
                    {
                        "fundId": group_fund.id,
                        "isCredit": True,
                        "amount": fee_per_month,
                        "groupId": member.groupId,
                        "groupCode": member.group.code if member.group else None,
                        "groupName": member.group.name if member.group else None,
                    },
                ]

                tx = ledger_repo.create_balanced_transaction(
                    db=db,
                    date=pay_date,
                    type="CONTRIBUTION",
                    reference_id=data.reference_number,
                    member_id=member.id,
                    donor_id=None,
                    notes=data.notes or f"Advance Dues for {m}/{y}",
                    created_by=current_user_id,
                    entries=entries,
                )
                last_tx_id = tx.id

                # Record individual ContributionPayment per month
                payment = ContributionPayment(
                    monthlyContributionId=contribution.id,
                    ledgerTransactionId=tx.id,
                    amount=fee_per_month,
                    paymentDate=pay_date,
                    paymentMethod=data.payment_method,
                    referenceNumber=data.reference_number,
                    notes=data.notes,
                    createdBy=current_user_id,
                )
                db.add(payment)

                paid_details.append(
                    PaidMonthDetail(
                        month=m,
                        year=y,
                        amount=fee_per_month,
                        monthly_contribution_id=contribution.id,
                    )
                )

            db.flush()

            # 3. Update contiguous paidUntil state
            paid_m, paid_y = contribution_repo.update_member_paid_until(db, member.id)

            # 4. Audit log
            audit_repo.log(
                db=db,
                action="ADVANCE_PAYMENT",
                module="MEMBERS",
                user_id=current_user_id,
                reference_id=last_tx_id,
                remarks=f"Collected advance dues ({len(unpaid_months)} months) for {member.memberId} - ৳{total_amount}",
            )

            db.commit()

            return DuePaymentResponse(
                success=True,
                member_id=member.id,
                total_amount_paid=total_amount,
                months_paid=paid_details,
                paid_until_month=paid_m,
                paid_until_year=paid_y,
                ledger_transaction_id=last_tx_id,
                message=f"Successfully collected {len(unpaid_months)} months advance dues.",
            )
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Multi-month advance collection failed: {str(e)}",
            )

    def get_member_dues_summary(self, db: Session, member_id: str) -> MemberDuesSummaryResponse:
        member = member_repo.get_by_id(db, member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member with ID '{member_id}' not found",
            )

        current_fee = settings_repo.get_monthly_membership_fee(db)

        # Total paid and pending
        contributions = member.contributions or []
        total_paid = sum(
            sum(p.amount for p in c.payments) for c in contributions
        )
        total_expected = sum(c.expectedAmount for c in contributions if not c.isAdditional)
        total_due = max(0, total_expected - total_paid)

        return MemberDuesSummaryResponse(
            member_id=member.id,
            member_code=member.memberId,
            full_name=member.fullName or "",
            mobile=member.mobile,
            group_id=member.groupId,
            group_name=member.group.name if member.group else "Unassigned",
            join_date=member.joinDate,
            current_monthly_fee=current_fee,
            paid_until_month=member.paidUntilMonth,
            paid_until_year=member.paidUntilYear,
            total_paid_amount=total_paid,
            total_due_amount=total_due,
            status=member.status,
        )

    def get_member_dues_ledger(
        self,
        db: Session,
        member_id: str,
        year: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> MemberDuesLedgerResponse:
        member = member_repo.get_by_id(db, member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member with ID '{member_id}' not found",
            )

        items, total = contribution_repo.get_member_dues_ledger(
            db=db,
            member_id=member_id,
            year=year,
            page=page,
            page_size=page_size,
        )

        ledger_items = []
        for c in items:
            p = c.payments[0] if c.payments else None
            paid_amount = sum(pay.amount for pay in c.payments)
            ledger_items.append(
                MemberDuesLedgerItem(
                    id=p.id if p else c.id,
                    monthly_contribution_id=c.id,
                    month=c.month,
                    year=c.year,
                    expected_amount=c.expectedAmount,
                    paid_amount=paid_amount,
                    is_additional=c.isAdditional,
                    status=c.status,
                    payment_date=p.paymentDate if p else None,
                    payment_method=p.paymentMethod if p else None,
                    reference_number=p.referenceNumber if p else None,
                    notes=p.notes if p else None,
                    ledger_transaction_id=p.ledgerTransactionId if p else None,
                )
            )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return MemberDuesLedgerResponse(
            member_id=member_id,
            items=ledger_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


dues_service = DuesService()
