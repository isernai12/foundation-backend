import datetime
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.organization import Group
from app.models.member import Member
from app.models.donor import Donor
from app.models.beneficiary import Beneficiary
from app.models.campaign import Campaign
from app.models.contribution import MonthlyContribution
from app.models.ledger import LedgerTransaction
from app.repositories import settings_repo


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


def create_sample_member(client: TestClient, group_id: str, name: str = "Dues Member", mobile: str = "01788776655") -> dict:
    token = get_token(client, "manager")
    res = client.post(
        "/api/v1/members",
        json={
            "group_id": group_id,
            "full_name": name,
            "mobile": mobile,
            "national_id": f"NID-{mobile}",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    return res.json()


def create_sample_beneficiary(db_session: Session, name: str = "Rashid Khan") -> Beneficiary:
    b = Beneficiary(
        beneficiaryId="BEN-0001",
        fullName=name,
        mobile="01811223344",
        nationalId="NID-BEN-01",
        status="ACTIVE",
    )
    db_session.add(b)
    db_session.flush()
    return b


# ===========================================================================
# 1. MONTHLY DUES TESTS
# ===========================================================================

def test_normal_monthly_payment(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    group_id = get_active_group_id(db_session)
    member = create_sample_member(client, group_id, "Monthly Due Member 1", "01711001101")

    res = client.post(
        "/api/v1/contributions/single",
        json={
            "member_id": member["id"],
            "month": 1,
            "year": 2026,
            "amount": 100,
            "payment_method": "CASH",
            "notes": "January 2026 dues",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert data["total_amount_paid"] == 100
    assert data["paid_until_month"] == 1
    assert data["paid_until_year"] == 2026


def test_duplicate_monthly_payment_prevention(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    group_id = get_active_group_id(db_session)
    member = create_sample_member(client, group_id, "Dup Member", "01711001102")

    # 1. First payment succeeds
    res1 = client.post(
        "/api/v1/contributions/single",
        json={
            "member_id": member["id"],
            "month": 2,
            "year": 2026,
            "amount": 100,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 201

    # 2. Duplicate payment for same month/year is rejected
    res2 = client.post(
        "/api/v1/contributions/single",
        json={
            "member_id": member["id"],
            "month": 2,
            "year": 2026,
            "amount": 100,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 409


def test_cross_year_multi_month_advance_payment(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    group_id = get_active_group_id(db_session)
    member = create_sample_member(client, group_id, "Advance Member", "01711001103")

    # Nov 2026 to Feb 2027 (4 months: 11/2026, 12/2026, 1/2027, 2/2027)
    res = client.post(
        "/api/v1/contributions/advance",
        json={
            "member_id": member["id"],
            "from_month": 11,
            "from_year": 2026,
            "to_month": 2,
            "to_year": 2027,
            "amount_per_month": 200,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["total_amount_paid"] == 800  # 4 months * 200
    assert len(data["months_paid"]) == 4
    assert data["paid_until_month"] == 2
    assert data["paid_until_year"] == 2027


def test_dynamic_settings_fee_and_historical_preservation(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    group_id = get_active_group_id(db_session)
    member = create_sample_member(client, group_id, "Dynamic Fee Member", "01711001104")

    # Set default fee to 150 in settings
    settings_repo.set_setting(db_session, "DEFAULT_MONTHLY_CONTRIBUTION", "150")

    # 1. Pay with dynamic setting fee
    res1 = client.post(
        "/api/v1/contributions/single",
        json={
            "member_id": member["id"],
            "month": 3,
            "year": 2026,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 201
    assert res1.json()["total_amount_paid"] == 150

    # 2. Change fee in settings to 300
    settings_repo.set_setting(db_session, "DEFAULT_MONTHLY_CONTRIBUTION", "300")

    # 3. Pay next month with new fee
    res2 = client.post(
        "/api/v1/contributions/single",
        json={
            "member_id": member["id"],
            "month": 4,
            "year": 2026,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 201
    assert res2.json()["total_amount_paid"] == 300

    # 4. Verify historical payment for Month 3 remains 150
    ledger_res = client.get(
        f"/api/v1/members/{member['id']}/dues/ledger",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ledger_res.status_code == 200
    items = ledger_res.json()["items"]
    m3 = next(i for i in items if i["month"] == 3)
    m4 = next(i for i in items if i["month"] == 4)
    assert m3["paid_amount"] == 150
    assert m4["paid_amount"] == 300


def test_member_dues_summary(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    group_id = get_active_group_id(db_session)
    member = create_sample_member(client, group_id, "Summary Member", "01711001105")

    res = client.get(
        f"/api/v1/members/{member['id']}/dues",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["member_id"] == member["id"]
    assert "current_monthly_fee" in data


# ===========================================================================
# 2. FINANCIAL ACTIVITIES & DISBURSEMENTS
# ===========================================================================

def test_financial_activity_lifecycle_income_and_disbursement(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    group_id = get_active_group_id(db_session)

    # 1. Create Financial Activity
    res_act = client.post(
        "/api/v1/financial-activities",
        json={
            "name": "Winter Relief 2026",
            "purpose": "Distribute blankets to poor families",
            "target_amount": 50000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_act.status_code == 201
    act = res_act.json()
    assert act["available_balance"] == 0

    # 2. Receive Income (External Donor)
    res_inc = client.post(
        f"/api/v1/financial-activities/{act['id']}/contribute",
        json={
            "contributor_type": "EXTERNAL",
            "donor_info": {
                "full_name": "Rahman Brothers Ltd",
                "mobile": "01755443322",
            },
            "amount": 20000,
            "remarks": "Corporate Winter CSR",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_inc.status_code == 201

    # Check updated balance
    act_check1 = client.get(f"/api/v1/financial-activities/{act['id']}", headers={"Authorization": f"Bearer {token}"})
    assert act_check1.json()["available_balance"] == 20000

    # 3. Create Beneficiary
    ben = create_sample_beneficiary(db_session, "Poor Beneficiary 1")

    # 4. Attempt disbursement exceeding available balance (must be rejected)
    res_excess = client.post(
        f"/api/v1/financial-activities/{act['id']}/disburse",
        json={
            "beneficiary_id": ben.id,
            "amount": 25000,
            "reason": "Excessive request",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_excess.status_code == 400

    # 5. Successful disbursement within available balance
    res_disb = client.post(
        f"/api/v1/financial-activities/{act['id']}/disburse",
        json={
            "beneficiary_id": ben.id,
            "amount": 8000,
            "reason": "Emergency Winter Aid",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_disb.status_code == 201
    assert res_disb.json()["remaining_balance"] == 12000

    # 6. Check Activity Ledger
    res_ledger = client.get(
        f"/api/v1/financial-activities/{act['id']}/ledger",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_ledger.status_code == 200
    ledger_data = res_ledger.json()
    assert ledger_data["current_balance"] == 12000
    assert len(ledger_data["items"]) == 2
    # Verify running balance
    assert ledger_data["items"][0]["type"] == "INCOME"
    assert ledger_data["items"][0]["running_balance"] == 20000
    assert ledger_data["items"][1]["type"] == "DISBURSEMENT"
    assert ledger_data["items"][1]["running_balance"] == 12000


def test_financial_activity_transaction_rollback(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    res_act = client.post(
        "/api/v1/financial-activities",
        json={
            "name": "Rollback Test Activity",
            "purpose": "Test atomicity",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_act.status_code == 201
    act_id = res_act.json()["id"]

    # Simulate database error during audit log writing
    with patch("app.services.financial_activity_service.audit_repo.log", side_effect=Exception("Audit failure")):
        res_inc = client.post(
            f"/api/v1/financial-activities/{act_id}/contribute",
            json={
                "contributor_type": "EXTERNAL",
                "donor_info": {
                    "full_name": "Test Donor",
                    "mobile": "01755112233",
                },
                "amount": 5000,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_inc.status_code == 500

    # Verify no CampaignContribution was committed
    from app.models.campaign import CampaignContribution
    stmt = select(CampaignContribution).where(CampaignContribution.campaignId == act_id)
    contributions = db_session.scalars(stmt).all()
    assert len(contributions) == 0
