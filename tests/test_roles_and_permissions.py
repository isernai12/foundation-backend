from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models.auth import Role, Permission, RolePermission, User


def get_token(client: TestClient, username: str = "manager") -> str:
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "TestPassword123!"},
    )
    return login_res.json()["access_token"]


def test_list_permissions_and_sync(client: TestClient):
    token = get_token(client, "superadmin")

    # 1. List permissions
    res = client.get("/api/v1/permissions", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 15
    assert "Members" in data["modules"]
    assert "Loans" in data["modules"]

    # 2. Sync permissions (idempotent)
    res_sync = client.post("/api/v1/permissions/sync", headers={"Authorization": f"Bearer {token}"})
    assert res_sync.status_code == 200
    assert res_sync.json()["success"] is True


def test_create_and_manage_custom_role(client: TestClient, db_session: Session):
    token = get_token(client, "superadmin")

    # Fetch some permission IDs
    perms = db_session.scalars(select(Permission).limit(3)).all()
    perm_ids = [p.id for p in perms]

    # 1. Create custom role
    res = client.post(
        "/api/v1/roles",
        json={
            "name": "Branch Auditor",
            "description": "Audits accounts and reports",
            "permission_ids": perm_ids,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    role_data = res.json()
    assert role_data["name"] == "Branch Auditor"
    assert role_data["permissions_count"] == len(perm_ids)
    role_id = role_data["id"]

    # 2. Update role permissions
    res_update = client.patch(
        f"/api/v1/roles/{role_id}",
        json={
            "description": "Updated auditor description",
            "permission_ids": [perm_ids[0]],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_update.status_code == 200
    assert res_update.json()["description"] == "Updated auditor description"
    assert res_update.json()["permissions_count"] == 1

    # 3. Delete role
    res_del = client.delete(f"/api/v1/roles/{role_id}", headers={"Authorization": f"Bearer {token}"})
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True


def test_super_admin_role_protection(client: TestClient, db_session: Session):
    token = get_token(client, "superadmin")
    sa_role = db_session.scalars(select(Role).where(Role.name == "Super Admin")).first()
    assert sa_role is not None

    # 1. Attempt to delete Super Admin role must be rejected
    res_del = client.delete(f"/api/v1/roles/{sa_role.id}", headers={"Authorization": f"Bearer {token}"})
    assert res_del.status_code == 400

    # 2. Attempt to rename Super Admin role must be rejected
    res_rename = client.patch(
        f"/api/v1/roles/{sa_role.id}",
        json={"name": "Regular Admin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_rename.status_code == 400


def test_delete_role_with_assigned_users_protection(client: TestClient, db_session: Session):
    token = get_token(client, "superadmin")
    manager_role = db_session.scalars(select(Role).where(Role.name == "Manager")).first()
    assert manager_role is not None

    # Manager role has an active user assigned, deletion must be blocked
    res_del = client.delete(f"/api/v1/roles/{manager_role.id}", headers={"Authorization": f"Bearer {token}"})
    assert res_del.status_code == 400


def test_permission_denial_for_unauthorized_role(client: TestClient):
    # Employee has View permissions only, cannot add roles
    token = get_token(client, "employee")

    res = client.post(
        "/api/v1/roles",
        json={"name": "Hacker Role"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
