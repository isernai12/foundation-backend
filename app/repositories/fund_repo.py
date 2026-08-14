from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session, joinedload
from app.models.fund import Fund
from app.models.organization import Group
from app.models.ledger import LedgerEntry
from app.repositories.base import BaseRepository


class FundRepository(BaseRepository[Fund]):
    def __init__(self):
        super().__init__(Fund)

    def get_by_id(self, db: Session, fund_id: str) -> Optional[Fund]:
        stmt = select(Fund).where(Fund.id == fund_id).options(joinedload(Fund.group))
        return db.scalars(stmt).first()

    def get_by_name(self, db: Session, name: str) -> Optional[Fund]:
        stmt = select(Fund).where(func.lower(Fund.name) == func.lower(name.strip())).options(joinedload(Fund.group))
        return db.scalars(stmt).first()

    def get_general_fund(self, db: Session) -> Fund:
        """
        Gets or creates the root General Foundation Fund (Fund with groupId == None).
        """
        stmt = select(Fund).where(Fund.groupId.is_(None))
        fund = db.scalars(stmt).first()
        if not fund:
            fund = Fund(
                name="General Foundation Fund",
                description="Main central unallocated foundation asset pool",
            )
            db.add(fund)
            db.flush()
        return fund

    def get_or_create_funds(self, db: Session, group_id: Optional[str] = None) -> Tuple[Fund, Fund]:
        """
        Returns (target_fund, general_fund).
        If group_id is None or matches the Foundation Group, target_fund is the General Fund.
        """
        general_fund = self.get_general_fund(db)

        if not group_id:
            return general_fund, general_fund

        stmt = select(Fund).where(Fund.groupId == group_id)
        group_fund = db.scalars(stmt).first()

        if not group_fund:
            group = db.get(Group, group_id)
            if not group:
                raise ValueError(f"Group with ID '{group_id}' not found")

            group_fund = Fund(
                groupId=group_id,
                name=f"{group.name} Fund",
                description=f"Automated dedicated fund for group {group.name}",
            )
            db.add(group_fund)
            db.flush()

        return group_fund, general_fund

    def get_fund_balance(self, db: Session, fund_id: str) -> int:
        stmt_credit = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            and_(LedgerEntry.fundId == fund_id, LedgerEntry.isCredit == True)
        )
        stmt_debit = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            and_(LedgerEntry.fundId == fund_id, LedgerEntry.isCredit == False)
        )
        credit = db.scalar(stmt_credit) or 0
        debit = db.scalar(stmt_debit) or 0
        return int(credit - debit)

    def search_and_paginate(
        self,
        db: Session,
        query: Optional[str] = None,
        group_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Fund], int]:
        stmt = select(Fund).options(joinedload(Fund.group))
        filters = []

        if group_id:
            filters.append(Fund.groupId == group_id)

        if query and query.strip():
            search = f"%{query.strip()}%"
            filters.append(
                or_(
                    Fund.name.ilike(search),
                    Fund.description.ilike(search),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        stmt = stmt.order_by(Fund.createdAt.desc())
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        items = list(db.scalars(stmt).all())
        return items, total


fund_repo = FundRepository()
