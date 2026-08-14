import datetime
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.organization import Group
from app.models.member import Member
from app.models.member_request import MemberRequest


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


def create_sample_request(
    client: TestClient,
    group_id: str,
    name: str = "Tariqul Islam",
    mobile: str = "01755112233",
    nid: str = "19951122334455667",
) -> dict:
    payload = {
        "group_id": group_id,
        "full_name": name,
        "father_name": "Sirajul Islam",
        "mobile": mobile,
        "national_id": nid,
        "id_document_type": "NID",
        "occupation": "Software Engineer",
        "monthly_income": 80000,
        "blood_group": "B+",
        "present_address": "Dhanmondi, Dhaka",
        "permanent_address": "Comilla",
        "emergency_contact_name": "Salma Islam",
        "emergency_contact_mobile": "01755112244",
        "emergency_contact_relation": "Sister",
        "reference_name": "Kabir Hossain",
        "reference_mobile": "01855112255",
        "reference_relation": "Friend",
        "reason_for_joining": "To contribute to community welfare.",
        "documents": [
            {
                "title": "Photo",
                "type": "IMAGE",
                "cloudinary_public_id": "mr_photo_1",
                "secure_url": "https://res.cloudinary.com/demo/mr_photo.jpg",
            }
        ],
    }
    res = client.post("/api/v1/member-requests", json=payload)
    assert res.status_code == 201
    return res.json()


def test_submit_public_member_request(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    year = datetime.datetime.now(datetime.timezone.utc).year

    data = create_sample_request(client, group_id, "Tariqul Islam", "01755112233")
    assert data["status"] == "PENDING"
    assert data["application_number"].startswith(f"MR-{year}-")
    assert len(data["application_number"]) == 13


def test_get_member_request_status_public(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    created = create_sample_request(client, group_id, "Status Check Applicant", "01755112288")

    # Public status check by application number
    res1 = client.get(f"/api/v1/member-requests/{created['application_number']}/status")
    assert res1.status_code == 200
    assert res1.json()["status"] == "PENDING"
    assert res1.json()["full_name"] == "Status Check Applicant"

    # Public status check by UUID
    res2 = client.get(f"/api/v1/member-requests/{created['id']}/status")
    assert res2.status_code == 200
    assert res2.json()["application_number"] == created["application_number"]


def test_generate_unique_application_number(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    year = datetime.datetime.now(datetime.timezone.utc).year

    res1 = create_sample_request(client, group_id, "Applicant One", "01766110001")
    res2 = create_sample_request(client, group_id, "Applicant Two", "01766110002")

    assert res1["application_number"] == f"MR-{year}-00001"
    assert res2["application_number"] == f"MR-{year}-00002"


def test_submit_request_disabled_group_rejected(client: TestClient, db_session: Session):
    disabled_id = get_disabled_group_id(db_session)

    res = client.post(
        "/api/v1/member-requests",
        json={
            "group_id": disabled_id,
            "full_name": "Illegal Group Applicant",
            "mobile": "01799887766",
        },
    )
    assert res.status_code == 400


def test_list_and_get_member_requests_protected(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    created = create_sample_request(client, group_id, "Protected List Target", "01777000011")

    token = get_token(client, "manager")
    res_list = client.get(
        "/api/v1/member-requests",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_list.status_code == 200
    items = res_list.json()["items"]
    assert len(items) >= 1

    # Get Detail
    res_detail = client.get(
        f"/api/v1/member-requests/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == created["id"]


def test_approve_member_request_transaction(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    created = create_sample_request(client, group_id, "Approved Person", "01788000011")

    token = get_token(client, "manager")

    # Approve request
    res = client.post(
        f"/api/v1/member-requests/{created['id']}/approve",
        json={"remarks": "Documents verified and approved."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "member_id" in data
    assigned_member_id = data["member_id"]

    # Verify Member was created in database
    stmt_member = select(Member).where(Member.memberId == assigned_member_id)
    member = db_session.scalars(stmt_member).first()
    assert member is not None
    assert member.fullName == "Approved Person"
    assert member.status == "ACTIVE"
    assert len(member.documents) == 1
    assert member.documents[0].title == "Member Photo"

    # Verify Request status updated
    stmt_req = select(MemberRequest).where(MemberRequest.id == created["id"])
    req = db_session.scalars(stmt_req).first()
    assert req.status == "APPROVED"
    assert req.approvedBy is not None
    assert req.createdMemberId == member.id


def test_reject_member_request(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    created = create_sample_request(client, group_id, "Reject Person", "01788000022")

    token = get_token(client, "manager")
    res = client.post(
        f"/api/v1/member-requests/{created['id']}/reject",
        json={"reason": "Incomplete documentation", "admin_message": "Please re-apply with NID copy."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"

    stmt_req = select(MemberRequest).where(MemberRequest.id == created["id"])
    req = db_session.scalars(stmt_req).first()
    assert req.status == "REJECTED"
    assert req.rejectionReason == "Incomplete documentation"


def test_approve_already_approved_request_fails(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    created = create_sample_request(client, group_id, "Double Approve Person", "01788000033")

    token = get_token(client, "manager")
    # First approval
    res1 = client.post(
        f"/api/v1/member-requests/{created['id']}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 200

    # Second approval fails
    res2 = client.post(
        f"/api/v1/member-requests/{created['id']}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 400


def test_unauthorized_member_request_endpoints(client: TestClient):
    client.cookies.clear()
    res = client.get("/api/v1/member-requests")
    assert res.status_code == 401


def test_permission_denied_for_member_request_approval(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    created = create_sample_request(client, group_id, "Forbidden Approval Target", "01788000044")

    # Employee has Members:View, but lacks Members:Add / Approve
    token = get_token(client, "employee")
    res = client.post(
        f"/api/v1/member-requests/{created['id']}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_approval_transaction_rollback(client: TestClient, db_session: Session):
    group_id = get_active_group_id(db_session)
    created = create_sample_request(client, group_id, "Rollback Target Person", "01788000099")

    token = get_token(client, "manager")

    # Simulate an error right during the approval transaction
    with patch("app.services.member_request_service.audit_repo.log", side_effect=Exception("Simulated failure")):
        res = client.post(
            f"/api/v1/member-requests/{created['id']}/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 500

    # Ensure no orphaned Member was committed to the database
    stmt_member = select(Member).where(Member.fullName == "Rollback Target Person")
    member = db_session.scalars(stmt_member).first()
    assert member is None
