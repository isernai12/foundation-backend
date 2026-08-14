import datetime
from typing import Optional, List, Set
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session, joinedload
from app.models.auth import User, Role, Permission, RolePermission, UserPermission
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    def get_by_id(self, db: Session, user_id: str) -> Optional[User]:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                joinedload(User.role).joinedload(Role.permissions).joinedload(RolePermission.permission),
                joinedload(User.userPermissions).joinedload(UserPermission.permission),
            )
        )
        return db.scalars(stmt).unique().first()

    def get_by_username_or_email(self, db: Session, identifier: str) -> Optional[User]:
        clean_id = identifier.strip()
        stmt = (
            select(User)
            .where(
                or_(
                    func.lower(User.username) == func.lower(clean_id),
                    func.lower(User.email) == func.lower(clean_id),
                )
            )
            .options(joinedload(User.role))
        )
        return db.scalars(stmt).first()

    def get_by_username(self, db: Session, username: str) -> Optional[User]:
        stmt = select(User).where(func.lower(User.username) == func.lower(username.strip()))
        return db.scalars(stmt).first()

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        if not email:
            return None
        stmt = select(User).where(func.lower(User.email) == func.lower(email.strip()))
        return db.scalars(stmt).first()

    def update_last_login(self, db: Session, user_id: str) -> None:
        user = db.get(User, user_id)
        if user:
            user.lastLogin = datetime.datetime.now(datetime.timezone.utc)
            db.commit()

    def get_user_permissions(self, db: Session, user_id: str) -> List[str]:
        """
        Gathers permissions from both the user's base Role and direct UserPermission overrides.
        Returns a list of strings formatted as 'Module:Action'.
        """
        user = self.get_by_id(db, user_id)
        if not user or not user.role:
            return []

        # Super Admin check is handled in RBAC service (returns wildcard ['*'])
        from app.rbac.service import is_super_admin
        if is_super_admin(user.role.name):
            return ["*"]

        permissions: Set[str] = set()

        # Add role permissions
        for rp in user.role.permissions:
            if rp.permission:
                permissions.add(f"{rp.permission.module}:{rp.permission.action}")

        # Add custom user permissions
        for up in user.userPermissions:
            if up.permission:
                permissions.add(f"{up.permission.module}:{up.permission.action}")

        return sorted(list(permissions))


user_repo = UserRepository()
