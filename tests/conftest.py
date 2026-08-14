import pytest
import datetime
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.auth import User, Role, Permission, RolePermission, UserPermission, UserSession
from backend.app.models.organization import Foundation, Group
from backend.app.models.member import Member, MemberStatusHistory
from backend.app.models.member_request import MemberRequest
from backend.app.models.document import Document
from backend.app.models.fund import Fund
from backend.app.models.donor import Donor
from backend.app.models.ledger import LedgerTransaction, LedgerEntry
from backend.app.core.database import engine, get_db
from backend.app.auth.security import get_password_hash
from backend.app.main import app


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

    # 1. Seed mock roles
    super_admin_role = Role(name="Super Admin", description="Full access")
    manager_role = Role(name="Manager", description="Branch Manager")
    employee_role = Role(name="Employee", description="General Employee")

    session.add_all([super_admin_role, manager_role, employee_role])
    session.flush()

    # 2. Seed mock permissions
    perm_members_view = Permission(module="Members", action="View", description="View members")
    perm_members_add = Permission(module="Members", action="Add", description="Add members")
    perm_members_edit = Permission(module="Members", action="Edit", description="Edit members")
    perm_members_delete = Permission(module="Members", action="Delete", description="Delete members")
    
    perm_groups_view = Permission(module="Groups", action="View", description="View groups")
    perm_groups_add = Permission(module="Groups", action="Add", description="Add groups")
    perm_groups_edit = Permission(module="Groups", action="Edit", description="Edit groups")

    perm_funds_view = Permission(module="Fund Collection", action="View", description="View funds")
    perm_funds_add = Permission(module="Fund Collection", action="Add", description="Add funds")
    perm_funds_edit = Permission(module="Fund Collection", action="Edit", description="Edit funds")

    perm_donors_view = Permission(module="Donors", action="View", description="View donors")
    perm_donors_receive = Permission(module="Donors", action="Receive Installment", description="Receive donations")
    perm_donors_add = Permission(module="Donors", action="Add", description="Add donors")

    perm_financial_support_view = Permission(module="Financial Support", action="View", description="View financial support")
    perm_financial_support_add = Permission(module="Financial Support", action="Add", description="Add financial support")

    perm_loans_view = Permission(module="Loans", action="View", description="View loans")
    perm_loans_add = Permission(module="Loans", action="Add", description="Add loans")
    perm_loans_edit = Permission(module="Loans", action="Edit", description="Edit loans")
    perm_loans_manage = Permission(module="Loans", action="Manage", description="Manage loans")
    perm_loans_approve = Permission(module="Loans", action="Approve", description="Approve loans")

    perm_beneficiaries_view = Permission(module="Beneficiaries", action="View", description="View beneficiaries")
    perm_beneficiaries_add = Permission(module="Beneficiaries", action="Add", description="Add beneficiaries")
    perm_beneficiaries_edit = Permission(module="Beneficiaries", action="Edit", description="Edit beneficiaries")

    perm_reports_view = Permission(module="Reports", action="View", description="View reports")

    session.add_all([
        perm_members_view,
        perm_members_add,
        perm_members_edit,
        perm_members_delete,
        perm_groups_view,
        perm_groups_add,
        perm_groups_edit,
        perm_funds_view,
        perm_funds_add,
        perm_funds_edit,
        perm_donors_view,
        perm_donors_receive,
        perm_donors_add,
        perm_financial_support_view,
        perm_financial_support_add,
        perm_loans_view,
        perm_loans_add,
        perm_loans_edit,
        perm_loans_manage,
        perm_loans_approve,
        perm_beneficiaries_view,
        perm_beneficiaries_add,
        perm_beneficiaries_edit,
        perm_reports_view,
    ])
    session.flush()

    # 3. Role Permissions
    session.add_all([
        # Manager has full Member, Group, Fund, Donor, Loans, Beneficiary, Reports permissions
        RolePermission(roleId=manager_role.id, permissionId=perm_members_view.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_members_add.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_members_edit.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_members_delete.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_groups_view.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_groups_add.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_groups_edit.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_funds_view.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_funds_add.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_funds_edit.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_donors_view.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_donors_receive.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_donors_add.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_financial_support_view.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_financial_support_add.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_loans_view.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_loans_add.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_loans_edit.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_loans_manage.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_beneficiaries_view.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_beneficiaries_add.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_beneficiaries_edit.id),
        RolePermission(roleId=manager_role.id, permissionId=perm_reports_view.id),
        # Employee has View permissions only
        RolePermission(roleId=employee_role.id, permissionId=perm_members_view.id),
        RolePermission(roleId=employee_role.id, permissionId=perm_groups_view.id),
        RolePermission(roleId=employee_role.id, permissionId=perm_funds_view.id),
        RolePermission(roleId=employee_role.id, permissionId=perm_donors_view.id),
        RolePermission(roleId=employee_role.id, permissionId=perm_financial_support_view.id),
        RolePermission(roleId=employee_role.id, permissionId=perm_loans_view.id),
        RolePermission(roleId=employee_role.id, permissionId=perm_beneficiaries_view.id),
        RolePermission(roleId=employee_role.id, permissionId=perm_reports_view.id),
    ])
    session.flush()

    # 4. Mock Users
    hashed_pwd = get_password_hash("TestPassword123!")

    super_user = User(
        name="Super Admin User",
        username="superadmin",
        email="superadmin@foundation.org",
        password=hashed_pwd,
        roleId=super_admin_role.id,
        status="ACTIVE",
    )

    manager_user = User(
        name="Manager User",
        username="manager",
        email="manager@foundation.org",
        password=hashed_pwd,
        roleId=manager_role.id,
        status="ACTIVE",
    )

    employee_user = User(
        name="Employee User",
        username="employee",
        email="employee@foundation.org",
        password=hashed_pwd,
        roleId=employee_role.id,
        status="ACTIVE",
    )

    inactive_user = User(
        name="Inactive User",
        username="inactive",
        email="inactive@foundation.org",
        password=hashed_pwd,
        roleId=employee_role.id,
        status="INACTIVE",
    )

    session.add_all([super_user, manager_user, employee_user, inactive_user])
    session.flush()

    # 5. Seed Organization & Groups
    foundation = Foundation(
        name="Foundation Test Org",
        description="Main Foundation Entity",
    )
    session.add(foundation)
    session.flush()

    foundation_group = Group(
        foundationId=foundation.id,
        name="Central HQ Group",
        code="GRP-HQ-ROOT",
        status="ACTIVE",
        isFoundationGroup=True,
        memberSignupEnabled=False,
    )

    active_group = Group(
        foundationId=foundation.id,
        name="Dhaka Branch",
        code="GRP-DHK-01",
        status="ACTIVE",
        isFoundationGroup=False,
        memberSignupEnabled=True,
    )

    disabled_group = Group(
        foundationId=foundation.id,
        name="Closed Branch",
        code="GRP-CLS-02",
        status="ACTIVE",
        isFoundationGroup=False,
        memberSignupEnabled=False,
    )

    session.add_all([foundation_group, active_group, disabled_group])
    session.flush()

    # 6. Seed Root General Fund
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
