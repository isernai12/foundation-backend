import re
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from backend.app.models.donor import Donor
from backend.app.repositories.base import BaseRepository


class DonorRepository(BaseRepository[Donor]):
    def __init__(self):
        super().__init__(Donor)

    def get_by_id(self, db: Session, donor_id: str) -> Optional[Donor]:
        stmt = select(Donor).where(Donor.id == donor_id)
        return db.scalars(stmt).first()

    def get_by_donor_id_str(self, db: Session, donor_id_str: str) -> Optional[Donor]:
        stmt = select(Donor).where(Donor.donorId == donor_id_str.strip())
        return db.scalars(stmt).first()

    def get_by_mobile(self, db: Session, mobile: str) -> Optional[Donor]:
        stmt = select(Donor).where(Donor.mobile == mobile.strip())
        return db.scalars(stmt).first()

    def generate_next_donor_id(self, db: Session) -> str:
        stmt = select(Donor.donorId)
        all_ids = db.scalars(stmt).all()

        max_num = 0
        existing_set = set()

        for did in all_ids:
            if not did:
                continue
            existing_set.add(did)
            match = re.search(r"(\d+)$", did)
            if match:
                try:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

        next_num = max_num + 1
        candidate = f"DNR-{next_num:04d}"
        while candidate in existing_set:
            next_num += 1
            candidate = f"DNR-{next_num:04d}"

        return candidate


donor_repo = DonorRepository()
