import json
import uuid
import datetime
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.member import Member
from backend.app.models.member_request import MemberRequest
from backend.app.models.document import Document
from backend.app.models.auth import User
from backend.app.schemas.member import DocumentItem, GroupSummary
from backend.app.schemas.member_request import (
    MemberRequestCreate,
    MemberRequestSubmitResponse,
    MemberRequestStatusResponse,
    MemberRequestDetailResponse,
    MemberRequestListResponse,
)
from backend.app.repositories import (
    member_request_repo,
    member_repo,
    group_repo,
    audit_repo,
)


def format_request_detail(req: MemberRequest) -> MemberRequestDetailResponse:
    group_summary = None
    if req.group:
        group_summary = GroupSummary(id=req.group.id, name=req.group.name, code=req.group.code)

    docs_list: List[DocumentItem] = []
    if req.documents:
        try:
            parsed = json.loads(req.documents)
            if isinstance(parsed, list):
                for d in parsed:
                    if isinstance(d, dict):
                        docs_list.append(
                            DocumentItem(
                                title=d.get("title", "Document"),
                                type=d.get("type", "IMAGE"),
                                cloudinary_public_id=d.get("cloudinaryPublicId") or d.get("cloudinary_public_id"),
                                secure_url=d.get("secureUrl") or d.get("secure_url"),
                            )
                        )
        except Exception:
            pass

    return MemberRequestDetailResponse(
        id=req.id,
        application_number=req.applicationNumber,
        status=req.status,
        full_name=req.fullName,
        father_name=req.fatherName,
        mother_name=req.motherName,
        gender=req.gender,
        dob=req.dob,
        national_id=req.nationalId,
        id_document_type=req.idDocumentType or "NID",
        occupation=req.occupation,
        monthly_income=req.monthlyIncome,
        blood_group=req.bloodGroup,
        education=req.education,
        marital_status=req.maritalStatus,
        mobile=req.mobile,
        alt_mobile=req.altMobile,
        email=req.email,
        phone=req.phone,
        present_address=req.presentAddress,
        permanent_address=req.permanentAddress,
        emergency_contact_name=req.emergencyContactName,
        emergency_contact_mobile=req.emergencyContactMobile,
        emergency_contact_relation=req.emergencyContactRelation,
        reference_name=req.referenceName,
        reference_mobile=req.referenceMobile,
        reference_relation=req.referenceRelation,
        group_id=req.groupId,
        group=group_summary,
        reason_for_joining=req.reasonForJoining,
        documents=docs_list,
        rejection_reason=req.rejectionReason,
        admin_message=req.adminMessage,
        approved_at=req.approvedAt,
        approved_by=req.approvedBy,
        created_member_id=req.createdMemberId,
        submitted_at=req.submittedAt,
        updated_at=req.updatedAt,
    )


class MemberRequestService:
    def submit_public_request(
        self,
        db: Session,
        data: MemberRequestCreate,
        client_info: Optional[Dict[str, str]] = None,
    ) -> MemberRequestSubmitResponse:
        # 1. Group check if requested
        if data.group_id:
            allowed, err = group_repo.check_signup_allowed(db, data.group_id)
            if not allowed:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

        # 2. Document formatting
        docs_json = None
        if data.documents:
            docs_json = json.dumps([d.model_dump() for d in data.documents])

        # 3. Generate unique application number with collision retry loop
        current_year = datetime.datetime.now(datetime.timezone.utc).year
        app_num = member_request_repo.generate_next_application_number(db, year=current_year)

        req = MemberRequest(
            applicationNumber=app_num,
            status="PENDING",
            fullName=data.full_name.strip(),
            fatherName=data.father_name.strip() if data.father_name else None,
            motherName=data.mother_name.strip() if data.mother_name else None,
            gender=data.gender,
            dob=data.dob,
            nationalId=data.national_id.strip() if data.national_id else None,
            idDocumentType=data.id_document_type or "NID",
            occupation=data.occupation.strip() if data.occupation else None,
            monthlyIncome=data.monthly_income,
            bloodGroup=data.blood_group,
            education=data.education,
            maritalStatus=data.marital_status,
            mobile=data.mobile.strip() if data.mobile else None,
            altMobile=data.alt_mobile.strip() if data.alt_mobile else None,
            email=data.email.strip() if data.email else None,
            phone=data.phone.strip() if data.phone else None,
            presentAddress=data.present_address.strip() if data.present_address else None,
            permanentAddress=data.permanent_address.strip() if data.permanent_address else None,
            emergencyContactName=data.emergency_contact_name.strip() if data.emergency_contact_name else None,
            emergencyContactMobile=data.emergency_contact_mobile.strip() if data.emergency_contact_mobile else None,
            emergencyContactRelation=data.emergency_contact_relation.strip() if data.emergency_contact_relation else None,
            referenceName=data.reference_name.strip() if data.reference_name else None,
            referenceMobile=data.reference_mobile.strip() if data.reference_mobile else None,
            referenceRelation=data.reference_relation.strip() if data.reference_relation else None,
            groupId=data.group_id,
            reasonForJoining=data.reason_for_joining,
            documents=docs_json,
        )

        db.add(req)
        db.flush()

        info = client_info or {}
        audit_repo.log(
            db=db,
            action="SUBMIT",
            module="MEMBER_REQUEST",
            reference_id=req.id,
            ip_address=info.get("ip_address"),
            browser=info.get("user_agent"),
            remarks=f"Submitted member request {req.applicationNumber} for {req.fullName}",
        )

        db.commit()
        db.refresh(req)

        return MemberRequestSubmitResponse(
            id=req.id,
            application_number=req.applicationNumber,
            status=req.status,
            message="Application submitted successfully",
        )

    def get_status(self, db: Session, identifier: str) -> MemberRequestStatusResponse:
        clean_id = identifier.strip()
        req = member_request_repo.get_by_application_number(db, clean_id)
        if not req:
            req = member_request_repo.get_by_id(db, clean_id)

        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member request '{identifier}' not found",
            )

        return MemberRequestStatusResponse(
            id=req.id,
            application_number=req.applicationNumber,
            status=req.status,
            full_name=req.fullName,
            submitted_at=req.submittedAt,
            approved_at=req.approvedAt,
            rejection_reason=req.rejectionReason,
            admin_message=req.adminMessage,
        )

    def list_requests(
        self,
        db: Session,
        status_filter: Optional[str] = None,
        group_id: Optional[str] = None,
        query: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> MemberRequestListResponse:
        items, total = member_request_repo.search_and_paginate(
            db=db,
            status=status_filter,
            group_id=group_id,
            query=query,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return MemberRequestListResponse(
            items=[format_request_detail(r) for r in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_request_detail(self, db: Session, request_id: str) -> MemberRequestDetailResponse:
        req = member_request_repo.get_by_id(db, request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member request '{request_id}' not found",
            )
        return format_request_detail(req)

    def approve_request(
        self,
        db: Session,
        request_id: str,
        approver: User,
        remarks: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transactional approval of a member request.
        Creates a new Member, copies documents, marks request APPROVED, and records AuditLog.
        Completely rolls back if any step fails.
        """
        req = member_request_repo.get_by_id(db, request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member request '{request_id}' not found",
            )

        if req.status == "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This member request has already been approved",
            )

        if req.status == "REJECTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot approve a rejected member request without re-opening",
            )

        if not req.groupId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group was not selected in application. Please assign a group before approval.",
            )

        # Validate target group
        allowed, err = group_repo.check_signup_allowed(db, req.groupId)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

        # Parse reference
        reference_str = None
        if req.referenceName or req.referenceMobile or req.referenceRelation:
            reference_str = json.dumps({
                "name": req.referenceName or "",
                "mobile": req.referenceMobile or "",
                "relation": req.referenceRelation or "",
            })

        # Parse dob
        dob_dt = None
        if req.dob:
            try:
                dob_dt = datetime.datetime.fromisoformat(req.dob)
            except Exception:
                pass

        try:
            # 1. Generate new sequential Member ID
            next_member_id = member_repo.generate_next_member_id(db)

            # 2. Create Member
            member = Member(
                memberId=next_member_id,
                groupId=req.groupId,
                fullName=req.fullName,
                fatherName=req.fatherName,
                motherName=req.motherName,
                gender=req.gender,
                dob=dob_dt,
                nationalId=req.nationalId,
                idDocumentType=req.idDocumentType or "NID",
                occupation=req.occupation,
                monthlyIncome=req.monthlyIncome,
                bloodGroup=req.bloodGroup,
                education=req.education,
                maritalStatus=req.maritalStatus,
                mobile=req.mobile,
                altMobile=req.altMobile,
                email=req.email,
                phone=req.phone,
                presentAddress=req.presentAddress,
                permanentAddress=req.permanentAddress,
                emergencyContactName=req.emergencyContactName,
                emergencyContactMobile=req.emergencyContactMobile,
                emergencyContactRelation=req.emergencyContactRelation,
                reference=reference_str,
                joinDate=req.submittedAt or datetime.datetime.now(datetime.timezone.utc),
                status="ACTIVE",
                memberType="REGULAR",
                position="GENERAL_MEMBER",
                reasonForJoining=req.reasonForJoining,
                declarationAccepted=True,
                createdBy=approver.id,
            )
            db.add(member)
            db.flush()

            # 3. Copy documents
            if req.documents:
                try:
                    docs_list = json.loads(req.documents)
                    if isinstance(docs_list, list):
                        for d in docs_list:
                            if isinstance(d, dict):
                                doc_title = d.get("title", "Document")
                                doc_obj = Document(
                                    documentNumber=f"DOC-{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}-{uuid.uuid4().hex[:6].upper()}",
                                    title="Member Photo" if doc_title == "Photo" else doc_title,
                                    type=d.get("type", "IMAGE"),
                                    cloudinaryPublicId=d.get("cloudinaryPublicId") or d.get("cloudinary_public_id"),
                                    secureUrl=d.get("secureUrl") or d.get("secure_url"),
                                    originalFilename=f"{doc_title.lower().replace(' ', '_')}.jpg",
                                    mimeType="image/jpeg",
                                    sizeBytes=0,
                                    targetType="MEMBER",
                                    memberId=member.id,
                                )
                                db.add(doc_obj)
                except Exception:
                    pass

            # 4. Update request status
            approver_name = approver.name or approver.username
            now_dt = datetime.datetime.now(datetime.timezone.utc)
            req.status = "APPROVED"
            req.approvedAt = now_dt
            req.approvedBy = approver_name
            req.createdMemberId = member.id
            if remarks:
                req.adminMessage = remarks

            # 5. Record Audit Log
            audit_repo.log(
                db=db,
                action="APPROVE",
                module="MEMBER_REQUEST",
                user_id=approver.id,
                reference_id=req.id,
                remarks=f"Approved member request {req.applicationNumber}, created member {member.memberId}",
            )

            db.commit()
            db.refresh(member)
            db.refresh(req)

            return {
                "status": "ok",
                "message": f"Member request {req.applicationNumber} approved successfully",
                "member_id": member.memberId,
                "member_uuid": member.id,
            }
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Approval transaction failed: {str(e)}",
            )

    def reject_request(
        self,
        db: Session,
        request_id: str,
        reason: str,
        admin_message: Optional[str] = None,
        rejecter: Optional[User] = None,
    ) -> Dict[str, Any]:
        req = member_request_repo.get_by_id(db, request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member request '{request_id}' not found",
            )

        if req.status == "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reject an already approved member request",
            )

        req.status = "REJECTED"
        req.rejectionReason = reason.strip()
        if admin_message:
            req.adminMessage = admin_message.strip()

        user_id = rejecter.id if rejecter else None
        audit_repo.log(
            db=db,
            action="REJECT",
            module="MEMBER_REQUEST",
            user_id=user_id,
            reference_id=req.id,
            remarks=f"Rejected member request {req.applicationNumber}. Reason: {reason}",
        )

        db.commit()
        db.refresh(req)

        return {
            "status": "ok",
            "message": f"Member request {req.applicationNumber} rejected",
            "application_number": req.applicationNumber,
            "rejection_reason": req.rejectionReason,
        }


member_request_service = MemberRequestService()
