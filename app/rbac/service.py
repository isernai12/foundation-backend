import re
from typing import List, Optional
from backend.app.rbac.constants import SUPER_ADMIN_ROLE_NAMES


def is_super_admin(role_name: Optional[str]) -> bool:
    """
    Canonical helper to determine if a role string represents Super Admin.
    Matches Next.js isSuperAdminRole logic.
    """
    if not role_name:
        return False
    cleaned = re.sub(r"[\s_-]+", "", role_name.strip().lower())
    if cleaned in {"superadmin", "adminsuper"}:
        return True
    return role_name.strip() in {"Super Admin", "SUPER_ADMIN"}


def has_permission(
    user_permissions: Optional[List[str]],
    module: str,
    action: str,
    role_name: Optional[str] = None,
) -> bool:
    """
    Universal Permission Checker matching frontend rbac-client.ts.

    Rules:
    1. Super Admin role ALWAYS bypasses all permission checks (returns True).
    2. Wildcard permission ("*") grants access to everything.
    3. Action "Manage" or "*" grants full access within a module.
    4. Synonyms supported: "create" <-> "add", "view" matches "view*".
    """
    # 1. HARDCODED SUPER_ADMIN BYPASS
    if role_name and is_super_admin(role_name):
        return True

    permissions = user_permissions or []

    # Wildcard permission ("*")
    if "*" in permissions:
        return True

    if not module or not action:
        return False

    target_module = module.strip().lower()
    target_action = action.strip().lower()

    for perm in permissions:
        if perm == "*":
            return True

        parts = perm.split(":", 1)
        if len(parts) != 2:
            continue

        perm_module = parts[0].strip().lower()
        perm_action = parts[1].strip().lower()

        # Module matching
        if perm_module == target_module or perm_module == "*":
            # Action matching with canonical synonyms
            if (
                perm_action == target_action
                or perm_action == "*"
                or perm_action == "manage"
                or (target_action == "create" and perm_action == "add")
                or (target_action == "add" and perm_action == "create")
                or (target_action == "view" and perm_action.startswith("view"))
            ):
                return True

    return False
