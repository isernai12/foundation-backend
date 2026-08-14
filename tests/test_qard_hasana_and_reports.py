import datetime
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models.organization import Group
from backend.app.models.member import Member
from backend.app.models.beneficiary import Beneficiary
from backend.app.models.loan import Loan, LoanRepayment


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


def create_sample_member(client: TestClient, group_id: str, name: str = "Loan Member", mobile: str = "01733445566") -> dict:
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


# ===========================================================================
# 1. BENEFICIARY TESTS
# ===========================================================================

def test_create_and_get_beneficiary(client: TestClient, db_session: Session):
    token = get_token(client, "manager")

    res = client.post(
        "/api/v1/beneficiaries",
        json={
            "full_name": "Rahim Uddin",
            "mobile": "01855667788",
            "address": "Sonargaon, Narayanganj",
            "assistance_type": "QARD_HASANA",
            "occupation": "Small Trader",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    b = res.json()
    assert b["full_name"] == "Rahim Uddin"
    assert b["beneficiary_id"].startswith("BEN-")

    # Get details
    get_res = client.get(f"/api/v1/beneficiaries/{b['id']}", headers={"Authorization": f"Bearer {token}"})
    assert get_res.status_code == 200
    assert get_res.json()["full_name"] == "Rahim Uddin"


# ===========================================================================
# 2. QARD-E-HASANA TESTS
# ===========================================================================

def test_qard_hasana_lifecycle_disbursement_and_repayments(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    group_id = get_active_group_id(db_session)
    member = create_sample_member(client, group_id, "Qard Member 1", "01766554433")

    # 1. Disburse Qard-e-Hasana of ৳10,000
    res_loan = client.post(
        "/api/v1/qard-e-hasana",
        json={
            "member_id": member["id"],
            "amount": 10000,
            "loan_type": "BUSINESS",
            "business_type": "Grocery Store Restocking",
            "purpose": "Working capital for small shop",
            "installment_type": "MONTHLY",
            "installment_amount": 2500,
            "total_installments": 4,
            "notes": "Guaranteed by local village committee",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_loan.status_code == 201
    loan = res_loan.json()
    assert loan["amount"] == 10000
    assert loan["remaining_balance"] == 10000
    assert loan["total_paid_amount"] == 0
    assert loan["status"] == "ACTIVE"
    assert loan["loan_number"].startswith("L-")

    # 2. First Repayment: ৳2,500
    res_rep1 = client.post(
        f"/api/v1/qard-e-hasana/{loan['id']}/repayments",
        json={
            "amount": 2500,
            "installment_no": 1,
            "payment_method": "CASH",
            "reference_number": "REC-001",
            "notes": "First installment paid",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_rep1.status_code == 201
    rep1 = res_rep1.json()
    assert rep1["amount"] == 2500
    assert rep1["remaining_loan_balance"] == 7500
    assert rep1["loan_status"] == "ACTIVE"

    # 3. Overpayment prevention: Attempting to repay ৳8,000 when remaining is ৳7,500 must fail
    res_excess = client.post(
        f"/api/v1/qard-e-hasana/{loan['id']}/repayments",
        json={
            "amount": 8000,
            "payment_method": "CASH",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_excess.status_code == 400

    # 4. Final Full Repayment: ৳7,500
    res_rep2 = client.post(
        f"/api/v1/qard-e-hasana/{loan['id']}/repayments",
        json={
            "amount": 7500,
            "installment_no": 2,
            "payment_method": "CASH",
            "reference_number": "REC-002",
            "notes": "Final settlement",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_rep2.status_code == 201
    rep2 = res_rep2.json()
    assert rep2["amount"] == 7500
    assert rep2["remaining_loan_balance"] == 0
    assert rep2["loan_status"] == "PAID"

    # 5. Check Ledger
    res_ledger = client.get(
        f"/api/v1/qard-e-hasana/{loan['id']}/ledger",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_ledger.status_code == 200
    ledger_data = res_ledger.json()
    assert ledger_data["original_amount"] == 10000
    assert ledger_data["total_repaid"] == 10000
    assert ledger_data["current_balance"] == 0
    assert ledger_data["status"] == "PAID"
    assert len(ledger_data["items"]) == 3  # 1 disbursement + 2 repayments

    # Verify chronological running balance: 10000 -> 7500 -> 0
    assert ledger_data["items"][0]["type"] == "DISBURSEMENT"
    assert ledger_data["items"][0]["running_balance"] == 10000
    assert ledger_data["items"][1]["type"] == "REPAYMENT"
    assert ledger_data["items"][1]["running_balance"] == 7500
    assert ledger_data["items"][2]["type"] == "REPAYMENT"
    assert ledger_data["items"][2]["running_balance"] == 0


def test_qard_hasana_transaction_rollback(client: TestClient, db_session: Session):
    token = get_token(client, "manager")
    group_id = get_active_group_id(db_session)
    member = create_sample_member(client, group_id, "Rollback Loan Member", "01799887766")

    # Simulate database error during audit log writing
    with patch("backend.app.services.loan_service.audit_repo.log", side_effect=Exception("Database lock error simulation")):
        res = client.post(
            "/api/v1/qard-e-hasana",
            json={
                "member_id": member["id"],
                "amount": 15000,
                "purpose": "Rollback Test Qard",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 500

    # Verify no Loan row was committed
    stmt = select(Loan).where(Loan.memberId == member["id"])
    loan = db_session.scalars(stmt).first()
    assert loan is None


# ===========================================================================
# 3. FINANCIAL SUMMARY REPORT TEST
# ===========================================================================

def test_financial_summary_report(client: TestClient, db_session: Session):
    token = get_token(client, "manager")

    res = client.get(
        "/api/v1/reports/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    report = res.json()
    assert "overall" in report
    assert "groups" in report
    assert "monthly_dues_total" in report["overall"]
    assert "sadaqah_total" in report["overall"]
    assert "financial_activities_balance" in report["overall"]
    assert "qard_hasana_outstanding" in report["overall"]
    assert len(report["groups"]) >= 1
