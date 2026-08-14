import datetime
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session, joinedload
from backend.app.models.contribution import MonthlyContribution, ContributionPayment
from backend.app.models.member import Member
from backend.app.repositories.base import BaseRepository


class ContributionRepository(BaseRepository[MonthlyContribution]):
    def __init__(self):
        super().__init__(MonthlyContribution)

    def get_contribution(
        self,
        db: Session,
        member_id: str,
        month: int,
        year: int,
        is_additional: bool = False,
    ) -> Optional[MonthlyContribution]:
        stmt = (
            select(MonthlyContribution)
            .where(
                and_(
                    MonthlyContribution.memberId == member_id,
                    MonthlyContribution.month == month,
                    MonthlyContribution.year == year,
                    MonthlyContribution.isAdditional == is_additional,
                )
            )
            .options(joinedload(MonthlyContribution.payments))
        )
        return db.scalars(stmt).first()

    def update_member_paid_until(self, db: Session, member_id: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Calculates contiguous paid months starting from the earliest recorded month
        and updates Member.paidUntilMonth and Member.paidUntilYear.
        """
        stmt = (
            select(MonthlyContribution.month, MonthlyContribution.year)
            .where(
                and_(
                    MonthlyContribution.memberId == member_id,
                    MonthlyContribution.status == "PAID",
                    MonthlyContribution.isAdditional == False,
                )
            )
            .order_by(MonthlyContribution.year.asc(), MonthlyContribution.month.asc())
        )
        paid_records = db.execute(stmt).all()

        if not paid_records:
            member = db.get(Member, member_id)
            if member:
                member.paidUntilMonth = None
                member.paidUntilYear = None
                db.flush()
            return None, None

        # Build set of paid (year, month)
        paid_set = {(r.year, r.month) for r in paid_records}

        # Find contiguous chain starting from first paid month
        first_year, first_month = paid_records[0].year, paid_records[0].month
        cur_y, cur_m = first_year, first_month
        max_y, max_m = cur_y, cur_m

        while (cur_y, cur_m) in paid_set:
            max_y, max_m = cur_y, cur_m
            cur_m += 1
            if cur_m > 12:
                cur_m = 1
                cur_y += 1

        member = db.get(Member, member_id)
        if member:
            member.paidUntilMonth = max_m
            member.paidUntilYear = max_y
            db.flush()

        return max_m, max_y

    def get_member_dues_ledger(
        self,
        db: Session,
        member_id: str,
        year: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[MonthlyContribution], int]:
        stmt = (
            select(MonthlyContribution)
            .where(MonthlyContribution.memberId == member_id)
            .options(joinedload(MonthlyContribution.payments))
        )
        if year:
            stmt = stmt.where(MonthlyContribution.year == year)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        stmt = stmt.order_by(MonthlyContribution.year.desc(), MonthlyContribution.month.desc())
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        items = list(db.scalars(stmt).unique().all())
        return items, total


contribution_repo = ContributionRepository()
