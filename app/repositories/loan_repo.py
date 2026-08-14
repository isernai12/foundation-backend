import re
import datetime
from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session, joinedload
from backend.app.models.loan import Loan, LoanRepayment
from backend.app.models.member import Member
from backend.app.models.beneficiary import Beneficiary
from backend.app.models.ledger import LedgerTransaction, LedgerEntry
from backend.app.repositories.base import BaseRepository


class LoanRepository(BaseRepository[Loan]):
    def __init__(self):
        super().__init__(Loan)

    def get_by_id(self, db: Session, loan_id: str) -> Optional[Loan]:
        stmt = (
            select(Loan)
            .where(Loan.id == loan_id)
            .options(
                joinedload(Loan.member),
                joinedload(Loan.beneficiary),
                joinedload(Loan.repayments),
            )
        )
        return db.scalars(stmt).unique().first()

    def get_by_loan_number(self, db: Session, loan_number: str) -> Optional[Loan]:
        stmt = select(Loan).where(Loan.loanNumber == loan_number.strip())
        return db.scalars(stmt).first()

    def generate_next_loan_number(self, db: Session) -> str:
        year = datetime.datetime.now(datetime.timezone.utc).year
        stmt = select(Loan.loanNumber).where(Loan.loanNumber.like(f"L-{year}-%"))
        all_numbers = db.scalars(stmt).all()

        max_num = 0
        existing_set = set(all_numbers)

        for num_str in all_numbers:
            match = re.search(r"(\d+)$", num_str)
            if match:
                try:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

        next_num = max_num + 1
        candidate = f"L-{year}-{next_num:04d}"
        while candidate in existing_set:
            next_num += 1
            candidate = f"L-{year}-{next_num:04d}"

        return candidate

    def search_and_paginate(
        self,
        db: Session,
        query: Optional[str] = None,
        status_filter: Optional[str] = None,
        member_id: Optional[str] = None,
        beneficiary_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Loan], int]:
        stmt = select(Loan).options(
            joinedload(Loan.member),
            joinedload(Loan.beneficiary),
        )
        filters = []

        if status_filter:
            filters.append(Loan.status == status_filter)

        if member_id:
            filters.append(Loan.memberId == member_id)

        if beneficiary_id:
            filters.append(Loan.beneficiaryId == beneficiary_id)

        if query and query.strip():
            search = f"%{query.strip()}%"
            filters.append(
                or_(
                    Loan.loanNumber.ilike(search),
                    Loan.purpose.ilike(search),
                    Loan.notes.ilike(search),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        stmt = stmt.order_by(Loan.createdAt.desc())
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        items = list(db.scalars(stmt).unique().all())
        return items, total

    def get_loan_ledger_entries(self, db: Session, loan_id: str) -> List[dict]:
        loan = self.get_by_id(db, loan_id)
        if not loan:
            return []

        entries = []

        # 1. Initial Disbursement
        entries.append({
            "id": loan.id,
            "date": loan.disbursedDate or loan.requestedDate,
            "created_at": loan.createdAt,
            "type": "DISBURSEMENT",
            "amount": loan.amount,
            "payment_method": None,
            "reference_number": loan.loanNumber,
            "notes": f"Disbursed Qard-e-Hasana: {loan.purpose}",
        })

        # 2. Repayments (directly from loaded repayments collection)
        for r in loan.repayments:
            entries.append({
                "id": r.id,
                "date": r.date,
                "created_at": r.createdAt,
                "type": "REPAYMENT",
                "amount": r.amount,
                "payment_method": r.paymentMethod,
                "reference_number": r.referenceNumber,
                "notes": r.notes or f"Installment #{r.installmentNo or 1}",
            })

        entries.sort(key=lambda x: (x["date"], x["created_at"]))

        # Calculate running balance: starts at principal, decrements by each repayment
        running = loan.amount
        for item in entries:
            if item["type"] == "DISBURSEMENT":
                item["running_balance"] = loan.amount
            else:
                running -= item["amount"]
                item["running_balance"] = max(0, running)

        return entries


loan_repo = LoanRepository()
