import datetime
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models.organization import Group
from backend.app.models.member import Member
from backend.app.models.donor import Donor
from backend.app.models.fund import Fund
from backend.app.models.ledger import LedgerTransaction, LedgerEntry


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


def get_foundation_group_id(db_session: Session) -> str:
    stmt = select(Group).where(Group.isFoundationGroup == True)
    group = db_session.scalars(stmt).first()
    return group.id


def create_sample_member(client: TestClient, group_id: str, name: str = "Sadaqah Member", mobile: str = "01788112233") -> dict:
    token = get_token(client, "manager")
    res = client.post(
        "/api/v1/members",
        json={
            "group_id": group_id,
            "full_name": name,
            "mobile": mobile,
            "national_id": "19981122334455667",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    return res.json()


# ===========================================================================
# 1. GROUP TESTS
# ===========================================================================

def test_create_and_get_group(client: TestClient, db_session: Session):
    token = get_token(client, "manager")

    payload = {
        "name": "Chittagong Central",
        "code": "GRP-CTG-01",
        "short_name": "CTG-01",
        "description": "Port City Branch",
        "status": "ACTIVE",
        "is_foundation_group": False,
        "member_signup_enabled": True,
    }

    res = client.post(
        "/api/v1/groups",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Chittagong Central"
    assert data["code"] == "GRP-CTG-01"
    assert data["member_signup_enabled"] is True

    # Get group detail
    get_res = client.get(
        f"/api/v1/groups/{data['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["code"] == "GRP-CTG-01"


def test_update_and_search_groups(client: TestClient, db_session: Session):
    token = get_token(client, "manager")

    # Search
    res_search = client.get(
        "/api/v1/groups?query=Dhaka",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_search.status_code == 200
    assert len(res_search.json()["items"]) >= 1

    # Update
    group_id = get_active_group_id(db_session)
    res_update = client.patch(
        f"/api/v1/groups/{group_id}",
        json={"remarks": "Updated branch remarks via API"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_update.status_code == 200
    assert res_update.json()["remarks"] == "Updated branch remarks via API"


def test_foundation_group_restrictions(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    fg_id = get_foundation_group_id(db_session)

    # 1. Attempt to enable member signup on the root foundation group must be rejected
    res1 = client.patch(
        f"/api/v1/groups/{fg_id}",
        json={"member_signup_enabled": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 400

    # 2. Attempt to create a second foundation group must be rejected
    res2 = client.post(
        "/api/v1/groups",
        json={
            "name": "Second Foundation HQ",
            "code": "GRP-HQ-DUPLICATE",
            "is_foundation_group": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 400


# ===========================================================================
# 2. FUND TESTS
# ===========================================================================

def test_create_and_list_funds(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    group_id = get_active_group_id(db_session)

    # Create dedicated fund
    res = client.post(
        "/api/v1/funds",
        json={
            "name": "Winter Blanket Distribution Fund",
            "description": "Seasonal relief fund for cold weather",
            "group_id": group_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    fund_data = res.json()
    assert fund_data["name"] == "Winter Blanket Distribution Fund"
    assert fund_data["current_balance"] == 0

    # List funds
    list_res = client.get("/api/v1/funds", headers={"Authorization": f"Bearer {token}"})
    assert list_res.status_code == 200
    assert len(list_res.json()["items"]) >= 1


# ===========================================================================
# 3. DONATION / SADAQAH TESTS
# ===========================================================================

def test_receive_external_donor_sadaqah_with_inline_donor(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    group_id = get_active_group_id(db_session)

    payload = {
        "contributor_type": "EXTERNAL",
        "donor_info": {
            "full_name": "Haji Mohammad Ali",
            "mobile": "01711223344",
            "address": "Gulshan, Dhaka",
        },
        "group_id": group_id,
        "amount": 15000,
        "purpose": "General Sadaqah for Village Group",
        "payment_method": "CASH",
    }

    res = client.post(
        "/api/v1/sadaqah",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == 15000
    assert data["contributor_type"] == "EXTERNAL"
    assert data["donor_name"] == "Haji Mohammad Ali"
    assert data["donor_id"] is not None
    assert data["member_id"] is None

    # Check Group live balance updated
    group_res = client.get(f"/api/v1/groups/{group_id}", headers={"Authorization": f"Bearer {token}"})
    assert group_res.status_code == 200
    assert group_res.json()["current_balance"] == 15000


def test_receive_member_voluntary_sadaqah(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    group_id = get_active_group_id(db_session)

    # 1. Create Member
    member = create_sample_member(client, group_id, "Member Contributor", "01799001122")

    # 2. Member voluntarily contributes Sadaqah
    sadaqah_res = client.post(
        "/api/v1/sadaqah",
        json={
            "contributor_type": "MEMBER",
            "member_id": member["id"],
            "group_id": group_id,
            "amount": 5000,
            "purpose": "Voluntary Ramadan Sadaqah",
            "payment_method": "CASH",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sadaqah_res.status_code == 201
    data = sadaqah_res.json()
    assert data["amount"] == 5000
    assert data["contributor_type"] == "MEMBER"
    assert data["member_id"] == member["id"]
    assert data["member_name"] == "Member Contributor"
    assert data["donor_id"] is None

    # 3. Verify member profile dues and status remain unchanged
    m_check = client.get(f"/api/v1/members/{member['id']}", headers={"Authorization": f"Bearer {token}"})
    assert m_check.status_code == 200
    assert m_check.json()["status"] == "ACTIVE"


def test_contributor_rules_validation(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    group_id = get_active_group_id(db_session)
    member = create_sample_member(client, group_id, "Rule Validation Member", "01788554433")

    # 1. Providing both member_id and donor_id must be rejected
    res_both = client.post(
        "/api/v1/sadaqah",
        json={
            "contributor_type": "MEMBER",
            "member_id": member["id"],
            "donor_id": "some-donor-uuid",
            "amount": 1000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_both.status_code == 400

    # 2. Member contributor without member_id must be rejected
    res_missing_member = client.post(
        "/api/v1/sadaqah",
        json={
            "contributor_type": "MEMBER",
            "amount": 1000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_missing_member.status_code == 400

    # 3. Non-positive amount must be rejected
    res_zero = client.post(
        "/api/v1/sadaqah",
        json={
            "contributor_type": "MEMBER",
            "member_id": member["id"],
            "amount": 0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_zero.status_code == 422


def test_sadaqah_to_foundation_group(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    fg_id = get_foundation_group_id(db_session)

    # External donation assigned to central Foundation Group
    res = client.post(
        "/api/v1/sadaqah",
        json={
            "contributor_type": "EXTERNAL",
            "donor_info": {
                "full_name": "Anonymous Philanthropist",
                "mobile": "01700998877",
            },
            "group_id": fg_id,
            "amount": 50000,
            "purpose": "Central Foundation Donation",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    assert res.json()["amount"] == 50000


def test_sadaqah_transaction_rollback(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    group_id = get_active_group_id(db_session)
    member = create_sample_member(client, group_id, "Rollback Member", "01788990011")

    # Simulate database failure right during audit log writing
    with patch("backend.app.services.sadaqah_service.audit_repo.log", side_effect=Exception("Database lock error simulation")):
        res = client.post(
            "/api/v1/sadaqah",
            json={
                "contributor_type": "MEMBER",
                "member_id": member["id"],
                "group_id": group_id,
                "amount": 25000,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 500

    # Verify no orphaned LedgerTransaction was committed
    stmt = select(LedgerTransaction).where(LedgerTransaction.memberId == member["id"])
    tx = db_session.scalars(stmt).first()
    assert tx is None


def test_sadaqah_authorization_checks(client: TestClient):
    client.cookies.clear()
    # Unauthenticated request rejected
    res1 = client.get("/api/v1/sadaqah")
    assert res1.status_code == 401

    res2 = client.post("/api/v1/sadaqah", json={"amount": 500, "contributor_type": "MEMBER"})
    assert res2.status_code == 401
