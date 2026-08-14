import datetime
from typing import List, Optional, Dict
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from app.models.auth import Role, Permission, RolePermission, User
from app.schemas.role import (
    PermissionItem,
    RoleCreateRequest,
    RoleUpdateRequest,
    RoleDetailResponse,
    RoleListResponse,
    PermissionListResponse,
)
from app.rbac.service import is_super_admin
from app.rbac.registry import PERMISSION_REGISTRY, SYSTEM_MODULES
from app.repositories import audit_repo


def get_permission_metadata_map() -> Dict[str, dict]:
    meta_map = {}
    for p in PERMISSION_REGISTRY:
        key = f"{p.module.lower()}:{p.action.lower()}"
        meta_map[key] = {
            "code": p.code,
            "description": p.description,
            "name_en": p.name_en,
            "name_bn": p.name_bn,
        }
    return meta_map


def format_permission_item(p: Permission, meta_map: Dict[str, dict]) -> PermissionItem:
    key = f"{p.module.lower()}:{p.action.lower()}"
    meta = meta_map.get(key, {})
    code = meta.get("code", f"{p.module.lower().replace(' ', '_')}:{p.action.lower()}")
    return PermissionItem(
        id=p.id,
        module=p.module,
        action=p.action,
        code=code,
        description=p.description or meta.get("description"),
        name_en=meta.get("name_en", f"{p.action} {p.module}"),
        name_bn=meta.get("name_bn", f"{p.module} {p.action}"),
    )


def format_role_response(r: Role, db: Session, meta_map: Dict[str, dict]) -> RoleDetailResponse:
    # User count
    stmt_uc = select(func.count(User.id)).where(User.roleId == r.id)
    user_count = db.scalar(stmt_uc) or 0

    is_sa = is_super_admin(r.name)

    # Permissions
    perm_items = []
    if is_sa:
        # Super admin has wildcard access over all permissions
        stmt_all = select(Permission).order_by(Permission.module.asc(), Permission.action.asc())
        all_perms = db.scalars(stmt_all).all()
        perm_items = [format_permission_item(p, meta_map) for p in all_perms]
    else:
        for rp in r.permissions:
            if rp.permission:
                perm_items.append(format_permission_item(rp.permission, meta_map))

    return RoleDetailResponse(
        id=r.id,
        name=r.name,
        description=r.description,
        is_super_admin=is_sa,
        user_count=user_count,
        permissions_count=len(perm_items),
        permissions=perm_items,
        created_at=r.createdAt,
        updated_at=r.updatedAt,
    )


class RoleService:
    def sync_permissions(self, db: Session) -> int:
        """
        Idempotently seeds all standard permissions from PERMISSION_REGISTRY into the database
        without altering or deleting existing records.
        """
        inserted = 0
        for item in PERMISSION_REGISTRY:
            stmt = select(Permission).where(
                and_(
                    func.lower(Permission.module) == item.module.lower(),
                    func.lower(Permission.action) == item.action.lower(),
                )
            )
            existing = db.scalars(stmt).first()
            if not existing:
                p = Permission(
                    module=item.module,
                    action=item.action,
                    description=item.description,
                )
                db.add(p)
                inserted += 1

        if inserted > 0:
            db.commit()
        return inserted

    def list_permissions(self, db: Session) -> PermissionListResponse:
        self.sync_permissions(db)
        stmt = select(Permission).order_by(Permission.module.asc(), Permission.action.asc())
        perms = db.scalars(stmt).all()
        meta_map = get_permission_metadata_map()

        items = [format_permission_item(p, meta_map) for p in perms]
        return PermissionListResponse(
            items=items,
            total=len(items),
            modules=SYSTEM_MODULES,
        )

    def list_roles(self, db: Session) -> RoleListResponse:
        stmt = (
            select(Role)
            .options(joinedload(Role.permissions).joinedload(RolePermission.permission))
            .order_by(Role.createdAt.asc())
        )
        roles = db.scalars(stmt).unique().all()
        meta_map = get_permission_metadata_map()

        items = [format_role_response(r, db, meta_map) for r in roles]
        return RoleListResponse(items=items, total=len(items))

    def get_role(self, db: Session, role_id: str) -> RoleDetailResponse:
        stmt = (
            select(Role)
            .where(Role.id == role_id)
            .options(joinedload(Role.permissions).joinedload(RolePermission.permission))
        )
        role = db.scalars(stmt).unique().first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID '{role_id}' not found",
            )
        meta_map = get_permission_metadata_map()
        return format_role_response(role, db, meta_map)

    def create_role(
        self,
        db: Session,
        data: RoleCreateRequest,
        current_user_id: Optional[str] = None,
    ) -> RoleDetailResponse:
        role_name = data.name.strip()
        if is_super_admin(role_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create custom role using reserved Super Admin name.",
            )

        stmt_dup = select(Role).where(func.lower(Role.name) == func.lower(role_name))
        if db.scalars(stmt_dup).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role with name '{role_name}' already exists.",
            )

        role = Role(
            name=role_name,
            description=data.description,
        )
        db.add(role)
        db.flush()

        # Assign permissions
        if data.permission_ids:
            for pid in set(data.permission_ids):
                perm = db.get(Permission, pid)
                if perm:
                    rp = RolePermission(roleId=role.id, permissionId=perm.id)
                    db.add(rp)

        audit_repo.log(
            db=db,
            action="CREATE_ROLE",
            module="ROLES_PERMISSIONS",
            user_id=current_user_id,
            reference_id=role.id,
            remarks=f"Created custom role '{role.name}' with {len(data.permission_ids or [])} permissions",
        )

        db.commit()
        db.refresh(role)
        meta_map = get_permission_metadata_map()
        return format_role_response(role, db, meta_map)

    def update_role(
        self,
        db: Session,
        role_id: str,
        data: RoleUpdateRequest,
        current_user_id: Optional[str] = None,
    ) -> RoleDetailResponse:
        role = db.get(Role, role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID '{role_id}' not found",
            )

        is_sa = is_super_admin(role.name)

        if is_sa and data.name and not is_super_admin(data.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot rename the protected Super Admin system role.",
            )

        if data.name:
            new_name = data.name.strip()
            if new_name.lower() != role.name.lower():
                existing = db.scalars(select(Role).where(func.lower(Role.name) == func.lower(new_name))).first()
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Role name '{new_name}' is already in use.",
                    )
                role.name = new_name

        if data.description is not None:
            role.description = data.description

        # Update permissions if provided and not Super Admin
        if data.permission_ids is not None and not is_sa:
            # Delete old mappings
            stmt_del = select(RolePermission).where(RolePermission.roleId == role.id)
            old_rps = db.scalars(stmt_del).all()
            for rp in old_rps:
                db.delete(rp)
            db.flush()

            # Insert new mappings
            for pid in set(data.permission_ids):
                perm = db.get(Permission, pid)
                if perm:
                    db.add(RolePermission(roleId=role.id, permissionId=perm.id))

        audit_repo.log(
            db=db,
            action="UPDATE_ROLE",
            module="ROLES_PERMISSIONS",
            user_id=current_user_id,
            reference_id=role.id,
            remarks=f"Updated role '{role.name}'",
        )

        db.commit()
        db.refresh(role)
        meta_map = get_permission_metadata_map()
        return format_role_response(role, db, meta_map)

    def delete_role(
        self,
        db: Session,
        role_id: str,
        current_user_id: Optional[str] = None,
    ) -> dict:
        role = db.get(Role, role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID '{role_id}' not found",
            )

        # 1. Strictly Protect Super Admin Role
        if is_super_admin(role.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Super Admin system role cannot be deleted.",
            )

        # 2. Check Active Users assigned to this role
        stmt_users = select(func.count(User.id)).where(User.roleId == role.id)
        user_count = db.scalar(stmt_users) or 0
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete role '{role.name}' because {user_count} active user(s) are assigned to it. Reassign users first.",
            )

        role_name = role.name
        # Delete permission mappings
        stmt_rps = select(RolePermission).where(RolePermission.roleId == role.id)
        for rp in db.scalars(stmt_rps).all():
            db.delete(rp)

        db.delete(role)

        audit_repo.log(
            db=db,
            action="DELETE_ROLE",
            module="ROLES_PERMISSIONS",
            user_id=current_user_id,
            reference_id=role_id,
            remarks=f"Deleted custom role '{role_name}'",
        )

        db.commit()
        return {
            "success": True,
            "message": f"Successfully deleted role '{role_name}'.",
        }


role_service = RoleService()
