from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.auth import User
from backend.app.rbac.dependencies import (
    require_super_admin,
    require_role,
    require_permission,
)
from backend.app.rbac.service import is_super_admin, has_permission

# Define test router with protected endpoints to verify RBAC dependencies
rbac_test_router = APIRouter(prefix="/test-rbac", tags=["Test RBAC"])


@rbac_test_router.get("/super-admin-only")
def super_admin_endpoint(user: User = Depends(require_super_admin)):
    return {"message": "Hello Super Admin", "user": user.username}


@rbac_test_router.get("/manager-or-above")
def manager_endpoint(user: User = Depends(require_role("Manager"))):
    return {"message": "Hello Manager", "user": user.username}


@rbac_test_router.get("/members-view")
def members_view_endpoint(user: User = Depends(require_permission("Members", "View"))):
    return {"message": "Members View OK", "user": user.username}


@rbac_test_router.get("/members-create")
def members_create_endpoint(user: User = Depends(require_permission("Members", "Create"))):
    return {"message": "Members Create OK", "user": user.username}


@rbac_test_router.get("/unauthorized-action")
def unauthorized_action_endpoint(user: User = Depends(require_permission("SystemAdministration", "DangerousAction"))):
    return {"message": "Should not reach here", "user": user.username}


# Mount test routes
app.include_router(rbac_test_router)


def get_user_token(client: TestClient, username: str) -> str:
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "TestPassword123!"},
    )
    return login_res.json()["access_token"]


def test_rbac_service_helpers():
    # Super Admin detection
    assert is_super_admin("Super Admin") is True
    assert is_super_admin("SUPER_ADMIN") is True
    assert is_super_admin("superadmin") is True
    assert is_super_admin("adminsuper") is True
    assert is_super_admin("Manager") is False
    assert is_super_admin("Employee") is False
    assert is_super_admin(None) is False

    # Permission evaluation with synonyms
    perms = ["Members:Add", "Dashboard:View Dashboard"]
    assert has_permission(perms, "Members", "Add") is True
    assert has_permission(perms, "Members", "Create") is True  # Synonym create <-> add
    assert has_permission(perms, "Dashboard", "View") is True  # Synonym view -> view*
    assert has_permission(perms, "Members", "Delete") is False
    assert has_permission(perms, "Loans", "Approve") is False

    # Super Admin bypass
    assert has_permission([], "AnyModule", "AnyAction", role_name="Super Admin") is True


def test_super_admin_access_unconditional(client: TestClient):
    token = get_user_token(client, "superadmin")
    headers = {"Authorization": f"Bearer {token}"}

    # Super admin can access super-admin-only
    res1 = client.get("/test-rbac/super-admin-only", headers=headers)
    assert res1.status_code == 200

    # Super admin can access role-protected endpoints
    res2 = client.get("/test-rbac/manager-or-above", headers=headers)
    assert res2.status_code == 200

    # Super admin can access any permission-protected endpoint
    res3 = client.get("/test-rbac/unauthorized-action", headers=headers)
    assert res3.status_code == 200


def test_manager_role_access(client: TestClient):
    token = get_user_token(client, "manager")
    headers = {"Authorization": f"Bearer {token}"}

    # Manager cannot access super-admin-only
    res1 = client.get("/test-rbac/super-admin-only", headers=headers)
    assert res1.status_code == 403

    # Manager can access manager-or-above
    res2 = client.get("/test-rbac/manager-or-above", headers=headers)
    assert res2.status_code == 200

    # Manager has Members:View and Members:Add -> can view and create
    res3 = client.get("/test-rbac/members-view", headers=headers)
    assert res3.status_code == 200

    res4 = client.get("/test-rbac/members-create", headers=headers)
    assert res4.status_code == 200

    # Manager lacks unauthorized-action -> 403
    res5 = client.get("/test-rbac/unauthorized-action", headers=headers)
    assert res5.status_code == 403


def test_employee_role_access(client: TestClient):
    token = get_user_token(client, "employee")
    headers = {"Authorization": f"Bearer {token}"}

    # Employee cannot access manager-or-above
    res1 = client.get("/test-rbac/manager-or-above", headers=headers)
    assert res1.status_code == 403

    # Employee has Members:View -> can view
    res2 = client.get("/test-rbac/members-view", headers=headers)
    assert res2.status_code == 200

    # Employee lacks Members:Add / Create -> 403
    res3 = client.get("/test-rbac/members-create", headers=headers)
    assert res3.status_code == 403


def test_unauthenticated_requests_rejected(client: TestClient):
    client.cookies.clear()
    res1 = client.get("/test-rbac/members-view")
    assert res1.status_code == 401

    res2 = client.get("/test-rbac/super-admin-only")
    assert res2.status_code == 401
