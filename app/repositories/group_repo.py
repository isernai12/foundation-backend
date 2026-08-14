import datetime
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session
from backend.app.models.organization import Foundation, Group
from backend.app.models.member import Member
from backend.app.models.ledger import LedgerEntry
from backend.app.repositories.base import BaseRepository


class GroupRepository(BaseRepository[Group]):
    def __init__(self):
        super().__init__(Group)

    def get_by_id(self, db: Session, group_id: str) -> Optional[Group]:
        stmt = select(Group).where(Group.id == group_id)
        return db.scalars(stmt).first()

    def get_by_code(self, db: Session, code: str) -> Optional[Group]:
        stmt = select(Group).where(func.lower(Group.code) == func.lower(code.strip()))
        return db.scalars(stmt).first()

    def get_foundation_group(self, db: Session) -> Optional[Group]:
        stmt = select(Group).where(Group.isFoundationGroup == True)
        return db.scalars(stmt).first()

    def ensure_foundation_group(self, db: Session) -> Group:
        """
        Ensures the root Foundation and the single special Foundation Group exist.
        """
        foundation_group = self.get_foundation_group(db)
        if foundation_group:
            return foundation_group

        stmt_f = select(Foundation)
        foundation = db.scalars(stmt_f).first()
        if not foundation:
            foundation = Foundation(
                name="Main Foundation",
                description="Default Foundation Entity",
            )
            db.add(foundation)
            db.flush()

        code = "FOUNDATION-MAIN"
        existing = self.get_by_code(db, code)
        if existing:
            code = f"FOUNDATION-{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"

        foundation_group = Group(
            foundationId=foundation.id,
            name="Foundation Central",
            code=code,
            shortName="HQ",
            description="Foundation Central Fund & HQ Group",
            status="ACTIVE",
            isFoundationGroup=True,
            memberSignupEnabled=False,
        )
        db.add(foundation_group)
        db.commit()
        db.refresh(foundation_group)
        return foundation_group

    def check_signup_allowed(self, db: Session, group_id: str) -> Tuple[bool, Optional[str]]:
        group = self.get_by_id(db, group_id)
        if not group:
            return False, "Selected group does not exist."
        if not group.memberSignupEnabled:
            return False, "Member registration is disabled for the selected group."
        if group.isFoundationGroup:
            return False, "Cannot register members directly to the root foundation group."
        if group.status != "ACTIVE":
            return False, "Selected group is not active."
        return True, None

    def get_member_count(self, db: Session, group_id: str) -> int:
        stmt = select(func.count()).select_from(Member).where(
            and_(Member.groupId == group_id, Member.status != "DELETED")
        )
        return db.scalar(stmt) or 0

    def get_group_balance(self, db: Session, group_id: str) -> int:
        # Sum of credit entries minus debit entries for this group
        stmt_credit = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            and_(LedgerEntry.groupId == group_id, LedgerEntry.isCredit == True)
        )
        stmt_debit = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            and_(LedgerEntry.groupId == group_id, LedgerEntry.isCredit == False)
        )
        credit = db.scalar(stmt_credit) or 0
        debit = db.scalar(stmt_debit) or 0
        return int(credit - debit)

    def search_and_paginate(
        self,
        db: Session,
        query: Optional[str] = None,
        status_filter: Optional[str] = None,
        member_signup_enabled: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Group], int]:
        stmt = select(Group)
        filters = []

        if status_filter:
            filters.append(Group.status == status_filter)

        if member_signup_enabled is not None:
            filters.append(Group.memberSignupEnabled == member_signup_enabled)

        if query and query.strip():
            search = f"%{query.strip()}%"
            filters.append(
                or_(
                    Group.name.ilike(search),
                    Group.code.ilike(search),
                    Group.shortName.ilike(search),
                    Group.description.ilike(search),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Sort: Foundation Group first, then by createdAt desc
        stmt = stmt.order_by(Group.isFoundationGroup.desc(), Group.createdAt.desc())
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        items = list(db.scalars(stmt).all())
        return items, total


group_repo = GroupRepository()
