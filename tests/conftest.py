import pytest
import datetime
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.auth import User, Role, Permission, RolePermission, UserPermission, UserSession
from app.models.organization import Foundation, Group
from app.models.member import Member, MemberStatusHistory
from app.models.member_request import MemberRequest
from app.models.document import Document
from app.models.fund import Fund
from app.models.donor import Donor
from app.models.ledger import LedgerTransaction, LedgerEntry
from app.core.database import engine, get_db
from app.auth.security import get_password_hash
from app.main import app


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """
    Transactional test session using the real PostgreSQL connection.
    Every test runs inside an isolated transaction that is rolled back upon completion,
    preventing any persistent modifications or leftover test records in the database.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    def get_or_create_role(name: str, description: str) -> Role:
        role = session.query(Role).filter_by(name=name).first()
        if not role:
            role = Role(name=name, description=description)
            session.add(role)
            session.flush()
        return role

    def get_or_create_permission(module: str, action: str, description: str) -> Permission:
        perm = session.query(Permission).filter_by(module=module, action=action).first()
        if not perm:
            perm = Permission(module=module, action=action, description=description)
            session.add(perm)
            session.flush()
        return perm

    # 1. Seed / Get mock roles
    super_admin_role = get_or_create_role("Super Admin", "Full access")
    manager_role = get_or_create_role("Manager", "Branch Manager")
    employee_role = get_or_create_role("Employee", "General Employee")

    # 2. Seed / Get mock permissions
    perm_members_view = get_or_create_permission("Members", "View", "View members")
    perm_members_add = get_or_create_permission("Members", "Add", "Add members")
    perm_members_edit = get_or_create_permission("Members", "Edit", "Edit members")
    perm_members_delete = get_or_create_permission("Members", "Delete", "Delete members")
    
    perm_groups_view = get_or_create_permission("Groups", "View", "View groups")
    perm_groups_add = get_or_create_permission("Groups", "Add", "Add groups")
    perm_groups_edit = get_or_create_permission("Groups", "Edit", "Edit groups")
    perm_groups_delete = get_or_create_permission("Groups", "Delete", "Delete groups")

    perm_funds_view = get_or_create_permission("Fund Collection", "View", "View funds")
    perm_funds_add = get_or_create_permission("Fund Collection", "Add", "Add funds")
    perm_funds_edit = get_or_create_permission("Fund Collection", "Edit", "Edit funds")

    perm_donors_view = get_or_create_permission("Donors", "View", "View donors")
    perm_donors_receive = get_or_create_permission("Donors", "Receive Installment", "Receive donations")
    perm_donors_add = get_or_create_permission("Donors", "Add", "Add donors")

    perm_financial_support_view = get_or_create_permission("Financial Support", "View", "View financial support")
    perm_financial_support_add = get_or_create_permission("Financial Support", "Add", "Add financial support")

    perm_loans_view = get_or_create_permission("Loans", "View", "View loans")
    perm_loans_add = get_or_create_permission("Loans", "Add", "Add loans")
    perm_loans_edit = get_or_create_permission("Loans", "Edit", "Edit loans")
    perm_loans_manage = get_or_create_permission("Loans", "Manage", "Manage loans")
    perm_loans_approve = get_or_create_permission("Loans", "Approve", "Approve loans")

    perm_beneficiaries_view = get_or_create_permission("Beneficiaries", "View", "View beneficiaries")
    perm_beneficiaries_add = get_or_create_permission("Beneficiaries", "Add", "Add beneficiaries")
    perm_beneficiaries_edit = get_or_create_permission("Beneficiaries", "Edit", "Edit beneficiaries")

    perm_reports_view = get_or_create_permission("Reports", "View", "View reports")

    # 3. Role Permissions
    role_perms = [
        # Manager has full Member, Group, Fund, Donor, Loans, Beneficiary, Reports permissions
        (manager_role.id, perm_members_view.id),
        (manager_role.id, perm_members_add.id),
        (manager_role.id, perm_members_edit.id),
        (manager_role.id, perm_members_delete.id),
        (manager_role.id, perm_groups_view.id),
        (manager_role.id, perm_groups_add.id),
        (manager_role.id, perm_groups_edit.id),
        (manager_role.id, perm_groups_delete.id),
        (manager_role.id, perm_funds_view.id),
        (manager_role.id, perm_funds_add.id),
        (manager_role.id, perm_funds_edit.id),
        (manager_role.id, perm_donors_view.id),
        (manager_role.id, perm_donors_receive.id),
        (manager_role.id, perm_donors_add.id),
        (manager_role.id, perm_financial_support_view.id),
        (manager_role.id, perm_financial_support_add.id),
        (manager_role.id, perm_loans_view.id),
        (manager_role.id, perm_loans_add.id),
        (manager_role.id, perm_loans_edit.id),
        (manager_role.id, perm_loans_manage.id),
        (manager_role.id, perm_beneficiaries_view.id),
        (manager_role.id, perm_beneficiaries_add.id),
        (manager_role.id, perm_beneficiaries_edit.id),
        (manager_role.id, perm_reports_view.id),
        # Employee has View permissions only
        (employee_role.id, perm_members_view.id),
        (employee_role.id, perm_groups_view.id),
        (employee_role.id, perm_funds_view.id),
        (employee_role.id, perm_donors_view.id),
        (employee_role.id, perm_financial_support_view.id),
        (employee_role.id, perm_loans_view.id),
        (employee_role.id, perm_beneficiaries_view.id),
        (employee_role.id, perm_reports_view.id),
    ]

    for rid, pid in role_perms:
        existing_rp = session.query(RolePermission).filter_by(roleId=rid, permissionId=pid).first()
        if not existing_rp:
            session.add(RolePermission(roleId=rid, permissionId=pid))
    session.flush()

    # 4. Mock Users
    hashed_pwd = get_password_hash("TestPassword123!")

    def get_or_create_user(name: str, username: str, email: str, role_id: str, status_str: str) -> User:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            user = User(
                name=name,
                username=username,
                email=email,
                password=hashed_pwd,
                roleId=role_id,
                status=status_str,
            )
            session.add(user)
            session.flush()
        else:
            user.password = hashed_pwd
            user.roleId = role_id
            user.status = status_str
            session.flush()
        return user

    super_user = get_or_create_user("Super Admin User", "superadmin", "superadmin@foundation.org", super_admin_role.id, "ACTIVE")
    manager_user = get_or_create_user("Manager User", "manager", "manager@foundation.org", manager_role.id, "ACTIVE")
    employee_user = get_or_create_user("Employee User", "employee", "employee@foundation.org", employee_role.id, "ACTIVE")
    inactive_user = get_or_create_user("Inactive User", "inactive", "inactive@foundation.org", employee_role.id, "INACTIVE")

    # 5. Seed Organization & Groups
    foundation = session.query(Foundation).first()
    if not foundation:
        foundation = Foundation(
            name="Foundation Test Org",
            description="Main Foundation Entity",
        )
        session.add(foundation)
        session.flush()

    def get_or_create_group(name: str, code: str, is_hq: bool, signup_enabled: bool) -> Group:
        grp = session.query(Group).filter_by(code=code).first()
        if not grp:
            grp = Group(
                foundationId=foundation.id,
                name=name,
                code=code,
                status="ACTIVE",
                isFoundationGroup=is_hq,
                memberSignupEnabled=signup_enabled,
            )
            session.add(grp)
            session.flush()
        return grp

    foundation_group = get_or_create_group("Central HQ Group", "GRP-HQ-ROOT", True, False)
    active_group = get_or_create_group("Dhaka Branch", "GRP-DHK-01", False, True)
    disabled_group = get_or_create_group("Closed Branch", "GRP-CLS-02", False, False)

    # 6. Seed Root General Fund
    general_fund = session.query(Fund).first()
    if not general_fund:
        general_fund = Fund(
            groupId=None,
            name="General Foundation Fund",
            description="Main central unallocated foundation asset pool",
        )
        session.add(general_fund)
        session.flush()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
