from typing import Set

# System Roles
SUPER_ADMIN_ROLE_NAMES: Set[str] = {
    "superadmin",
    "adminsuper",
    "super admin",
    "super_admin",
    "super-admin",
}

DEFAULT_SYSTEM_ROLES = [
    "Super Admin",
    "Admin",
    "Manager",
    "Cashier",
    "Employee",
]

# Standard Modules
MODULE_DASHBOARD = "Dashboard"
MODULE_MEMBERS = "Members"
MODULE_BENEFICIARIES = "Beneficiaries"
MODULE_DONORS = "Donors"
MODULE_FUND_COLLECTION = "Fund Collection"
MODULE_FINANCIAL_SUPPORT = "Financial Support"
MODULE_LOANS = "Loans"
MODULE_GRANTS = "Grants"
MODULE_GROUPS = "Groups"
MODULE_REPORTS = "Reports"
MODULE_SETTINGS = "Settings"
MODULE_USERS = "Users"
MODULE_ROLES_PERMISSIONS = "Roles & Permissions"
MODULE_AUDIT_LOGS = "Audit Logs"
