import re
import datetime
from typing import Optional, List, Tuple, Dict, Any, Set
from sqlalchemy import select, or_, func, and_
from sqlalchemy.orm import Session, joinedload
from app.models.member import Member, MemberStatusHistory
from app.models.organization import Group
from app.models.document import Document
from app.repositories.base import BaseRepository


class MemberRepository(BaseRepository[Member]):
    def __init__(self):
        super().__init__(Member)

    def get_by_id(self, db: Session, member_id: str) -> Optional[Member]:
        stmt = (
            select(Member)
            .where(Member.id == member_id)
            .options(
                joinedload(Member.group),
                joinedload(Member.documents),
                joinedload(Member.statusHistory),
            )
        )
        return db.scalars(stmt).unique().first()

    def get_by_member_id_str(self, db: Session, member_id_str: str) -> Optional[Member]:
        stmt = select(Member).where(Member.memberId == member_id_str.strip())
        return db.scalars(stmt).first()

    def find_conflicts(
        self,
        db: Session,
        national_id: Optional[str] = None,
        mobile: Optional[str] = None,
        email: Optional[str] = None,
        member_id: Optional[str] = None,
        exclude_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Checks for uniqueness conflicts on nationalId, mobile, email, and memberId.
        Returns (has_conflict, error_code).
        """
        conditions = []
        if national_id and national_id.strip():
            conditions.append(Member.nationalId == national_id.strip())
        if mobile and mobile.strip():
            conditions.append(Member.mobile == mobile.strip())
        if email and email.strip():
            conditions.append(func.lower(Member.email) == func.lower(email.strip()))
        if member_id and member_id.strip():
            conditions.append(Member.memberId == member_id.strip())

        if not conditions:
            return False, None

        stmt = select(Member).where(or_(*conditions))
        if exclude_id:
            stmt = stmt.where(Member.id != exclude_id)

        existing = db.scalars(stmt).first()
        if not existing:
            return False, None

        if national_id and existing.nationalId == national_id.strip():
            return True, "national_id_already_exists"
        if mobile and existing.mobile == mobile.strip():
            return True, "mobile_already_exists"
        if email and existing.email and existing.email.lower() == email.strip().lower():
            return True, "email_already_exists"
        if member_id and existing.memberId == member_id.strip():
            return True, "member_id_already_exists"

        return True, "unique_constraint_violation"

    def generate_next_member_id(self, db: Session) -> str:
        """
        Generates next sequential Member ID in standard format M-0001, M-0002...
        Safe, persistent, monotonic, never reuses deleted IDs.
        """
        stmt = select(Member.memberId)
        all_ids = db.scalars(stmt).all()

        max_num = 0
        existing_set: Set[str] = set()

        for mid in all_ids:
            if not mid:
                continue
            existing_set.add(mid)
            match = re.search(r"(\d+)$", mid)
            if match:
                try:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

        next_num = max_num + 1
        candidate = f"M-{next_num:04d}"
        while candidate in existing_set:
            next_num += 1
            candidate = f"M-{next_num:04d}"

        return candidate

    def search_and_paginate(
        self,
        db: Session,
        query: Optional[str] = None,
        group_id: Optional[str] = None,
        status: Optional[str] = None,
        member_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Member], int]:
        """
        Searches members with filters and server-side pagination.
        """
        stmt = select(Member).options(joinedload(Member.group))

        filters = []
        if status:
            filters.append(Member.status == status)
        else:
            # Default: exclude DELETED records
            filters.append(Member.status != "DELETED")

        if group_id:
            filters.append(Member.groupId == group_id)

        if member_type:
            filters.append(Member.memberType == member_type)

        if query and query.strip():
            search = f"%{query.strip()}%"
            filters.append(
                or_(
                    Member.fullName.ilike(search),
                    Member.memberId.ilike(search),
                    Member.mobile.ilike(search),
                    Member.nationalId.ilike(search),
                    Member.email.ilike(search),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        # Total count query
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Pagination and order
        stmt = stmt.order_by(Member.createdAt.desc())
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        items = list(db.scalars(stmt).unique().all())
        return items, total


member_repo = MemberRepository()
