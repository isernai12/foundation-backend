from typing import List, Callable, Sequence
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.auth import User
from app.auth.dependencies import get_current_active_user
from app.repositories import user_repo, audit_repo
from app.rbac.service import is_super_admin, has_permission


def require_authenticated_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Dependency ensuring user is authenticated and active."""
    return current_user


def require_active_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Alias for active user requirement."""
    return current_user


def require_super_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Dependency ensuring current user has Super Admin role.
    Rejects with 403 Forbidden otherwise.
    """
    role_name = current_user.role.name if current_user.role else None
    if not is_super_admin(role_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin privileges required",
        )
    return current_user


def require_role(*allowed_roles: str) -> Callable[[User], User]:
    """
    Dependency factory requiring user to possess one of the specified roles.
    Super Admin role automatically bypasses this check.
    """
    normalized_allowed = {r.strip().lower() for r in allowed_roles}

    def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        user_role = current_user.role.name if current_user.role else ""
        # Super Admin bypass
        if is_super_admin(user_role):
            return current_user

        if user_role.strip().lower() not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access requires one of the following roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


def require_permission(module: str, action: str) -> Callable[[User, Session], User]:
    """
    Dependency factory requiring user to have specific module:action permission.
    Super Admin role automatically bypasses all permission checks.
    Logs unauthorized attempts to AuditLog.
    """
    def permission_checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> User:
        user_role = current_user.role.name if current_user.role else None

        # 1. HARDCODED SUPER_ADMIN BYPASS
        if is_super_admin(user_role):
            return current_user

        # Fetch loaded permissions
        permissions = user_repo.get_user_permissions(db, current_user.id)
        is_allowed = has_permission(permissions, module, action, user_role)

        if not is_allowed:
            # Audit unauthorized access attempt
            audit_repo.log(
                db=db,
                action="UNAUTHORIZED_ACCESS",
                module=module,
                user_id=current_user.id,
                remarks=f"Unauthorized attempt to execute {action} on module {module}",
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {module}:{action} required",
            )

        return current_user

    return permission_checker
