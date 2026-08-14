from fastapi.testclient import TestClient
from backend.app.core.config import settings


def test_login_success_with_username(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "manager", "password": "TestPassword123!", "remember_me": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "manager"
    assert data["user"]["role"] == "Manager"
    assert "Members:View" in data["user"]["permissions"]
    assert "Members:Add" in data["user"]["permissions"]
    # Check cookie
    assert settings.SESSION_COOKIE_NAME in response.cookies


def test_login_success_with_email(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "superadmin@foundation.org", "password": "TestPassword123!", "remember_me": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "Super Admin"
    assert data["user"]["permissions"] == ["*"]


def test_login_invalid_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "manager", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Invalid" in response.json()["error"]["message"] or "Invalid" in str(response.json())


def test_login_nonexistent_user(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "nonexistent_user", "password": "AnyPassword!"},
    )
    assert response.status_code == 401


def test_login_inactive_user(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "inactive", "password": "TestPassword123!"},
    )
    assert response.status_code == 403


def test_get_me_authenticated_with_header(client: TestClient):
    # 1. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "manager", "password": "TestPassword123!"},
    )
    token = login_res.json()["access_token"]

    # 2. Get me with Bearer token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "manager"


def test_get_me_authenticated_with_cookie(client: TestClient):
    # 1. Login sets cookie in test client
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "manager", "password": "TestPassword123!"},
    )
    token = login_res.json()["access_token"]

    # 2. Request without explicit header (cookie automatically sent by test client)
    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "manager"


def test_get_me_unauthenticated(client: TestClient):
    client.cookies.clear()
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_logout_invalidates_session(client: TestClient):
    # 1. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "manager", "password": "TestPassword123!"},
    )
    token = login_res.json()["access_token"]

    # 2. Logout
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_res.status_code == 200

    # 3. Subsequent request with invalidated token should fail
    client.cookies.clear()
    subsequent_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert subsequent_res.status_code == 401
