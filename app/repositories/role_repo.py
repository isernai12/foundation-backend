from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload
from backend.app.models.auth import Role, RolePermission
from backend.app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self):
        super().__init__(Role)

    def get_by_name(self, db: Session, name: str) -> Optional[Role]:
        stmt = (
            select(Role)
            .where(func.lower(Role.name) == func.lower(name.strip()))
            .options(joinedload(Role.permissions).joinedload(RolePermission.permission))
        )
        return db.scalars(stmt).unique().first()

    def get_all(self, db: Session) -> List[Role]:
        stmt = select(Role).order_by(Role.name.asc())
        return list(db.scalars(stmt).all())


role_repo = RoleRepository()
