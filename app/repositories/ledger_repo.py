import datetime
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session, joinedload
from app.models.ledger import LedgerTransaction, LedgerEntry
from app.models.fund import Fund
from app.models.member import Member
from app.models.donor import Donor
from app.repositories.base import BaseRepository


class LedgerRepository(BaseRepository[LedgerTransaction]):
    def __init__(self):
        super().__init__(LedgerTransaction)

    def create_balanced_transaction(
        self,
        db: Session,
        date: datetime.datetime,
        type: str,
        reference_id: Optional[str] = None,
        member_id: Optional[str] = None,
        donor_id: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[str] = None,
        entries: List[Dict[str, Any]] = None,
    ) -> LedgerTransaction:
        """
        Creates a strictly balanced double-entry ledger transaction.
        Total Debits (isCredit == False) must equal Total Credits (isCredit == True) > 0.
        """
        if not entries:
            raise ValueError("Transaction must contain at least two balanced ledger entries.")

        total_debit = sum(e["amount"] for e in entries if not e["isCredit"])
        total_credit = sum(e["amount"] for e in entries if e["isCredit"])

        if total_debit != total_credit:
            raise ValueError(f"Ledger entries do not balance! Total debit: {total_debit}, Total credit: {total_credit}")

        if total_debit <= 0:
            raise ValueError("Transaction amount must be strictly positive (> 0).")

        tx = LedgerTransaction(
            date=date,
            type=type,
            referenceId=reference_id,
            memberId=member_id,
            donorId=donor_id,
            status="COMPLETED",
            notes=notes,
            createdBy=created_by,
        )
        db.add(tx)
        db.flush()

        for e in entries:
            entry_obj = LedgerEntry(
                transactionId=tx.id,
                fundId=e["fundId"],
                isCredit=e["isCredit"],
                amount=e["amount"],
                groupId=e.get("groupId"),
                groupCode=e.get("groupCode"),
                groupName=e.get("groupName"),
                createdBy=created_by,
            )
            db.add(entry_obj)

        db.flush()
        return tx

    def get_by_id(self, db: Session, tx_id: str) -> Optional[LedgerTransaction]:
        stmt = (
            select(LedgerTransaction)
            .where(LedgerTransaction.id == tx_id)
            .options(
                joinedload(LedgerTransaction.member),
                joinedload(LedgerTransaction.donor),
                joinedload(LedgerTransaction.entries).joinedload(LedgerEntry.fund),
            )
        )
        return db.scalars(stmt).unique().first()

    def search_donations_and_paginate(
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
    ) -> Tuple[List[LedgerTransaction], int, int]:
        """
        Searches donation/sadaqah transactions with filtering and pagination.
        Returns (items, total_count, total_amount).
        """
        stmt = (
            select(LedgerTransaction)
            .where(LedgerTransaction.type.in_(["DONATION", "SADAQAH", "VOLUNTARY_SADAQAH"]))
            .options(
                joinedload(LedgerTransaction.member),
                joinedload(LedgerTransaction.donor),
                joinedload(LedgerTransaction.entries).joinedload(LedgerEntry.fund),
            )
        )

        filters = []
        if contributor_type == "MEMBER":
            filters.append(LedgerTransaction.memberId.isnot(None))
        elif contributor_type in ["EXTERNAL", "DONOR"]:
            filters.append(LedgerTransaction.donorId.isnot(None))

        if member_id:
            filters.append(LedgerTransaction.memberId == member_id)

        if donor_id:
            filters.append(LedgerTransaction.donorId == donor_id)

        if start_date:
            filters.append(LedgerTransaction.date >= start_date)

        if end_date:
            filters.append(LedgerTransaction.date <= end_date)

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Total amount query across filtered transactions
        amount_stmt = (
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .select_from(LedgerEntry)
            .join(LedgerTransaction, LedgerTransaction.id == LedgerEntry.transactionId)
            .where(
                and_(
                    LedgerEntry.isCredit == True,
                    LedgerTransaction.type.in_(["DONATION", "SADAQAH", "VOLUNTARY_SADAQAH"]),
                    *filters,
                )
            )
        )
        total_amount = db.scalar(amount_stmt) or 0

        stmt = stmt.order_by(LedgerTransaction.date.desc(), LedgerTransaction.createdAt.desc())
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        items = list(db.scalars(stmt).unique().all())
        return items, total, int(total_amount)


ledger_repo = LedgerRepository()
