from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models.organization import Group
from backend.app.models.member import Member


def get_token(client: TestClient, username: str = "manager") -> str:
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "TestPassword123!"},
    )
    return login_res.json()["access_token"]


def get_active_group_id(db_session: Session) -> str:
    stmt = select(Group).where(Group.code == "GRP-DHK-01")
    group = db_session.scalars(stmt).first()
    return group.id


def get_disabled_group_id(db_session: Session) -> str:
    stmt = select(Group).where(Group.code == "GRP-CLS-02")
    group = db_session.scalars(stmt).first()
    return group.id


def create_sample_member(client: TestClient, group_id: str, name: str = "Rahim Ahmed", mobile: str = "01711000001", nid: str = "19901234567890123") -> dict:
    token = get_token(client, "manager")
    res = client.post(
        "/api/v1/members",
        json={
            "group_id": group_id,
            "full_name": name,
            "father_name": "Karim Ahmed",
            "mobile": mobile,
            "national_id": nid,
            "id_document_type": "NID",
            "occupation": "Teacher",
            "monthly_income": 35000,
            "blood_group": "A+",
            "present_address": "Mirpur 10, Dhaka",
            "permanent_address": "Gazipur",
            "emergency_contact_name": "Fatema Ahmed",
            "emergency_contact_mobile": "01711000002",
            "emergency_contact_relation": "Spouse",
            "reference_name": "Dr. Hasan",
            "reference_mobile": "01811000003",
            "reference_relation": "Colleague",
            "member_type": "REGULAR",
            "position": "GENERAL_MEMBER",
            "documents": [
                {
                    "title": "Member Photo",
                    "type": "IMAGE",
                    "cloudinary_public_id": "photo_123",
                    "secure_url": "https://res.cloudinary.com/demo/photo.jpg",
                }
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    return res.json()


def test_create_member_success(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    data = create_sample_member(client, group_id, "Rahim Ahmed", "01711000001", "19901234567890123")

    assert data["full_name"] == "Rahim Ahmed"
    assert data["member_id"] == "M-0001"
    assert data["status"] == "ACTIVE"
    assert data["group"]["id"] == group_id
    assert len(data["documents"]) == 1
    assert data["documents"][0]["title"] == "Member Photo"


def test_get_member_detail(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    created = create_sample_member(client, group_id, "Member Detail Test", "01711000011", "19901234567890011")

    token = get_token(client, "employee")  # Employee has Members:View
    res = client.get(f"/api/v1/members/{created['id']}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == created["id"]
    assert data["full_name"] == "Member Detail Test"
    assert data["group"]["code"] == "GRP-DHK-01"


def test_update_member(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    created = create_sample_member(client, group_id, "Update Test User", "01711000022", "19901234567890022")

    token = get_token(client, "manager")
    update_payload = {
        "full_name": "Update Test User (Updated)",
        "occupation": "Senior Teacher",
        "remarks": "Updated profile via API",
        "status": "ACTIVE",
    }

    res = client.patch(
        f"/api/v1/members/{created['id']}",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["full_name"] == "Update Test User (Updated)"
    assert data["occupation"] == "Senior Teacher"


def test_search_and_pagination_members(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    token = get_token(client, "manager")

    create_sample_member(client, group_id, "Sumon Chowdhury", "01722000002", "19929876543210987")
    create_sample_member(client, group_id, "Akbar Ali", "01722000003", "19929876543210988")

    # Search by name
    res_search = client.get(
        "/api/v1/members?query=Sumon",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_search.status_code == 200
    assert len(res_search.json()["items"]) == 1
    assert res_search.json()["items"][0]["full_name"] == "Sumon Chowdhury"

    # Search by mobile
    res_mobile = client.get(
        "/api/v1/members?query=01722000002",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_mobile.status_code == 200
    assert len(res_mobile.json()["items"]) == 1

    # Pagination test
    res_page = client.get(
        "/api/v1/members?page=1&page_size=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_page.status_code == 200
    data = res_page.json()
    assert len(data["items"]) == 1
    assert data["total"] == 2
    assert data["page_size"] == 1


def test_duplicate_member_id_prevention(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    token = get_token(client, "manager")

    create_sample_member(client, group_id, "Original Member", "01733000001", "19933333333333333")

    # Attempt to create member with already taken Member ID "M-0001"
    res = client.post(
        "/api/v1/members",
        json={
            "group_id": group_id,
            "full_name": "Duplicate Test",
            "member_id": "M-0001",
            "mobile": "01999888777",
            "national_id": "99988877766655544",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409


def test_duplicate_mobile_or_nid_prevention(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    token = get_token(client, "manager")

    create_sample_member(client, group_id, "First Person", "01744000001", "19944444444444444")

    # Duplicate mobile
    res_mobile = client.post(
        "/api/v1/members",
        json={
            "group_id": group_id,
            "full_name": "Duplicate Mobile",
            "mobile": "01744000001",  # Same mobile
            "national_id": "88877766655544433",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_mobile.status_code == 409

    # Duplicate NID
    res_nid = client.post(
        "/api/v1/members",
        json={
            "group_id": group_id,
            "full_name": "Duplicate NID",
            "mobile": "01911999888",
            "national_id": "19944444444444444",  # Same NID
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_nid.status_code == 409


def test_disabled_group_signup_rejected(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    disabled_id = get_disabled_group_id(db_session)

    res = client.post(
        "/api/v1/members",
        json={
            "group_id": disabled_id,
            "full_name": "Disabled Group Member",
            "mobile": "01811888777",
            "national_id": "77766655544433322",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "disabled" in res.json()["error"]["message"].lower() or "disabled" in str(res.json()).lower()


def test_unauthorized_access(client: TestClient):
    client.cookies.clear()
    res = client.get("/api/v1/members")
    assert res.status_code == 401


def test_permission_denied_for_member_creation(client: TestClient, db_session: Session):
    token = get_token(client, "employee")
    group_id = get_active_group_id(db_session)

    res = client.post(
        "/api/v1/members",
        json={
            "group_id": group_id,
            "full_name": "Forbidden Test",
            "mobile": "01788776655",
            "national_id": "66655544433322211",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_soft_delete_member(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    created = create_sample_member(client, group_id, "Delete Target", "01755000055", "19955555555555555")

    token = get_token(client, "manager")
    res = client.delete(
        f"/api/v1/members/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200

    # Verify excluded from normal list
    list_res = client.get("/api/v1/members", headers={"Authorization": f"Bearer {token}"})
    names = [m["full_name"] for m in list_res.json()["items"]]
    assert "Delete Target" not in names
