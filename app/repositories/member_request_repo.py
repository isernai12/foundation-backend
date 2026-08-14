import re
import datetime
from typing import Optional, List, Tuple, Set
from sqlalchemy import select, or_, func, and_
from sqlalchemy.orm import Session, joinedload
from app.models.member_request import MemberRequest
from app.repositories.base import BaseRepository


class MemberRequestRepository(BaseRepository[MemberRequest]):
    def __init__(self):
        super().__init__(MemberRequest)

    def get_by_id(self, db: Session, request_id: str) -> Optional[MemberRequest]:
        stmt = (
            select(MemberRequest)
            .where(MemberRequest.id == request_id)
            .options(joinedload(MemberRequest.group))
        )
        return db.scalars(stmt).unique().first()

    def get_by_application_number(self, db: Session, app_number: str) -> Optional[MemberRequest]:
        clean_num = app_number.strip()
        stmt = (
            select(MemberRequest)
            .where(func.lower(MemberRequest.applicationNumber) == func.lower(clean_num))
            .options(joinedload(MemberRequest.group))
        )
        return db.scalars(stmt).first()

    def generate_next_application_number(self, db: Session, year: Optional[int] = None) -> str:
        """
        Generates next sequential application number in standard format MR-YYYY-00001.
        Thread-safe, persistent, monotonic.
        """
        target_year = year or datetime.datetime.now(datetime.timezone.utc).year
        prefix = f"MR-{target_year}-"

        stmt = select(MemberRequest.applicationNumber).where(
            MemberRequest.applicationNumber.like(f"{prefix}%")
        )
        existing_numbers = db.scalars(stmt).all()

        max_num = 0
        existing_set: Set[str] = set()

        for app_num in existing_numbers:
            if not app_num:
                continue
            existing_set.add(app_num)
            match = re.match(rf"^MR-{target_year}-(\d+)$", app_num)
            if match:
                try:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

        next_num = max_num + 1
        candidate = f"{prefix}{next_num:05d}"
        while candidate in existing_set:
            next_num += 1
            candidate = f"{prefix}{next_num:05d}"

        return candidate

    def search_and_paginate(
        self,
        db: Session,
        status: Optional[str] = None,
        group_id: Optional[str] = None,
        query: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[MemberRequest], int]:
        """
        Searches member requests with filters and pagination.
        """
        stmt = select(MemberRequest).options(joinedload(MemberRequest.group))

        filters = []
        if status:
            filters.append(MemberRequest.status == status)

        if group_id:
            filters.append(MemberRequest.groupId == group_id)

        if query and query.strip():
            search = f"%{query.strip()}%"
            filters.append(
                or_(
                    MemberRequest.fullName.ilike(search),
                    MemberRequest.applicationNumber.ilike(search),
                    MemberRequest.mobile.ilike(search),
                    MemberRequest.nationalId.ilike(search),
                    MemberRequest.email.ilike(search),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        stmt = stmt.order_by(MemberRequest.submittedAt.desc())
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        items = list(db.scalars(stmt).unique().all())
        return items, total


member_request_repo = MemberRequestRepository()
