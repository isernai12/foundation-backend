import re
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from backend.app.models.beneficiary import Beneficiary
from backend.app.repositories.base import BaseRepository


class BeneficiaryRepository(BaseRepository[Beneficiary]):
    def __init__(self):
        super().__init__(Beneficiary)

    def get_by_id(self, db: Session, beneficiary_id: str) -> Optional[Beneficiary]:
        stmt = select(Beneficiary).where(Beneficiary.id == beneficiary_id)
        return db.scalars(stmt).first()

    def get_by_code(self, db: Session, code: str) -> Optional[Beneficiary]:
        stmt = select(Beneficiary).where(Beneficiary.beneficiaryId == code.strip())
        return db.scalars(stmt).first()

    def generate_next_beneficiary_id(self, db: Session) -> str:
        stmt = select(Beneficiary.beneficiaryId)
        all_ids = db.scalars(stmt).all()

        max_num = 0
        existing_set = set()

        for bid in all_ids:
            if not bid:
                continue
            existing_set.add(bid)
            match = re.search(r"(\d+)$", bid)
            if match:
                try:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

        next_num = max_num + 1
        candidate = f"BEN-{next_num:04d}"
        while candidate in existing_set:
            next_num += 1
            candidate = f"BEN-{next_num:04d}"

        return candidate


beneficiary_repo = BeneficiaryRepository()
