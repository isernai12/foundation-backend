import json
import uuid
import datetime
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.member import Member, MemberStatusHistory
from backend.app.models.document import Document
from backend.app.schemas.member import (
    MemberCreateRequest,
    MemberUpdateRequest,
    MemberResponse,
    MemberDetailResponse,
    MemberListResponse,
    GroupSummary,
    DocumentResponse,
    MemberStatusHistoryResponse,
    ReferenceInfo,
)
from backend.app.repositories import member_repo, group_repo, audit_repo


def format_reference_out(ref_str: Optional[str]) -> Optional[ReferenceInfo]:
    if not ref_str:
        return None
    try:
        data = json.loads(ref_str)
        if isinstance(data, dict):
            return ReferenceInfo(
                name=data.get("name"),
                mobile=data.get("mobile"),
                relation=data.get("relation"),
            )
    except Exception:
        pass
    return None


def format_member_response(m: Member) -> MemberResponse:
    return MemberResponse(
        id=m.id,
        member_id=m.memberId,
        group_id=m.groupId,
        group_name=m.group.name if m.group else None,
        group_code=m.group.code if m.group else None,
        full_name=m.fullName,
        mobile=m.mobile,
        email=m.email,
        status=m.status,
        member_type=m.memberType or "REGULAR",
        position=m.position or "GENERAL_MEMBER",
        join_date=m.joinDate,
        created_at=m.createdAt,
    )


def format_member_detail_response(m: Member) -> MemberDetailResponse:
    group_summary = None
    if m.group:
        group_summary = GroupSummary(id=m.group.id, name=m.group.name, code=m.group.code)

    docs_out = [
        DocumentResponse(
            id=d.id,
            document_number=d.documentNumber,
            title=d.title,
            type=d.type,
            cloudinary_public_id=d.cloudinaryPublicId,
            secure_url=d.secureUrl,
            size_bytes=d.sizeBytes,
        )
        for d in m.documents
    ]

    history_out = [
        MemberStatusHistoryResponse(
            id=h.id,
            from_status=h.fromStatus,
            to_status=h.toStatus,
            reason=h.reason,
            notes=h.notes,
            changed_by=h.changedBy,
            changed_at=h.changedAt,
        )
        for h in m.statusHistory
    ]

    return MemberDetailResponse(
        id=m.id,
        member_id=m.memberId,
        group_id=m.groupId,
        group=group_summary,
        full_name=m.fullName,
        father_name=m.fatherName,
        mother_name=m.motherName,
        gender=m.gender,
        dob=m.dob,
        national_id=m.nationalId,
        id_document_type=m.idDocumentType or "NID",
        occupation=m.occupation,
        monthly_income=m.monthlyIncome,
        blood_group=m.bloodGroup,
        mobile=m.mobile,
        alt_mobile=m.altMobile,
        email=m.email,
        phone=m.phone,
        present_address=m.presentAddress,
        permanent_address=m.permanentAddress,
        emergency_contact_name=m.emergencyContactName,
        emergency_contact_mobile=m.emergencyContactMobile,
        emergency_contact_relation=m.emergencyContactRelation,
        reference=format_reference_out(m.reference),
        join_date=m.joinDate,
        remarks=m.remarks,
        marital_status=m.maritalStatus,
        education=m.education,
        workplace=m.workplace,
        designation=m.designation,
        skills=m.skills,
        reason_for_joining=m.reasonForJoining,
        member_type=m.memberType or "REGULAR",
        position=m.position or "GENERAL_MEMBER",
        status=m.status,
        created_at=m.createdAt,
        updated_at=m.updatedAt,
        documents=docs_out,
        status_history=history_out,
    )


class MemberService:
    def list_members(
        self,
        db: Session,
        query: Optional[str] = None,
        group_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        member_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> MemberListResponse:
        items, total = member_repo.search_and_paginate(
            db=db,
            query=query,
            group_id=group_id,
            status=status_filter,
            member_type=member_type,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return MemberListResponse(
            items=[format_member_response(m) for m in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_member(self, db: Session, member_id: str) -> MemberDetailResponse:
        member = member_repo.get_by_id(db, member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member with ID '{member_id}' not found",
            )
        return format_member_detail_response(member)

    def create_member(
        self,
        db: Session,
        data: MemberCreateRequest,
        current_user_id: Optional[str] = None,
    ) -> MemberDetailResponse:
        # 1. Check target group signup eligibility
        allowed, err = group_repo.check_signup_allowed(db, data.group_id)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

        # 2. Check unique conflicts
        has_conflict, conflict_code = member_repo.find_conflicts(
            db=db,
            national_id=data.national_id,
            mobile=data.mobile,
            email=data.email,
            member_id=data.member_id,
        )
        if has_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate entry detected: {conflict_code}",
            )

        # 3. Generate sequential Member ID if not provided
        member_id_str = data.member_id or member_repo.generate_next_member_id(db)

        # 4. Serialize reference JSON
        reference_str = None
        ref = data.reference
        if ref and (ref.name or ref.mobile or ref.relation):
            reference_str = json.dumps({"name": ref.name or "", "mobile": ref.mobile or "", "relation": ref.relation or ""})
        elif data.reference_name or data.reference_mobile or data.reference_relation:
            reference_str = json.dumps({
                "name": data.reference_name or "",
                "mobile": data.reference_mobile or "",
                "relation": data.reference_relation or "",
            })

        member = Member(
            memberId=member_id_str,
            groupId=data.group_id,
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
            mobile=data.mobile.strip() if data.mobile else None,
            altMobile=data.alt_mobile.strip() if data.alt_mobile else None,
            email=data.email.strip() if data.email else None,
            phone=data.phone.strip() if data.phone else None,
            presentAddress=data.present_address.strip() if data.present_address else None,
            permanentAddress=data.permanent_address.strip() if data.permanent_address else None,
            emergencyContactName=data.emergency_contact_name.strip() if data.emergency_contact_name else None,
            emergencyContactMobile=data.emergency_contact_mobile.strip() if data.emergency_contact_mobile else None,
            emergencyContactRelation=data.emergency_contact_relation.strip() if data.emergency_contact_relation else None,
            reference=reference_str,
            joinDate=data.join_date or datetime.datetime.now(datetime.timezone.utc),
            status=data.status or "ACTIVE",
            remarks=data.remarks,
            maritalStatus=data.marital_status,
            education=data.education,
            workplace=data.workplace,
            designation=data.designation,
            skills=data.skills,
            reasonForJoining=data.reason_for_joining,
            declarationAccepted=True,
            memberType=data.member_type or "REGULAR",
            position=data.position or "GENERAL_MEMBER",
            createdBy=current_user_id,
        )

        db.add(member)
        db.flush()

        # 5. Handle documents
        if data.documents:
            for doc in data.documents:
                unique_doc_num = f"DOC-{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}-{uuid.uuid4().hex[:6].upper()}"
                doc_obj = Document(
                    documentNumber=unique_doc_num,
                    title=doc.title,
                    type=doc.type or "IMAGE",
                    cloudinaryPublicId=doc.cloudinary_public_id,
                    secureUrl=doc.secure_url,
                    originalFilename=f"{doc.title.lower().replace(' ', '_')}.jpg",
                    mimeType="image/jpeg",
                    sizeBytes=0,
                    targetType="MEMBER",
                    memberId=member.id,
                )
                db.add(doc_obj)

        audit_repo.log(
            db=db,
            action="CREATE",
            module="MEMBER",
            user_id=current_user_id,
            reference_id=member.id,
            remarks=f"Created member {member.memberId} ({member.fullName})",
        )

        db.commit()
        db.refresh(member)
        return format_member_detail_response(member)

    def update_member(
        self,
        db: Session,
        member_id: str,
        data: MemberUpdateRequest,
        current_user_id: Optional[str] = None,
    ) -> MemberDetailResponse:
        member = member_repo.get_by_id(db, member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member with ID '{member_id}' not found",
            )

        # 1. Group check if updated
        if data.group_id and data.group_id != member.groupId:
            allowed, err = group_repo.check_signup_allowed(db, data.group_id)
            if not allowed:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
            member.groupId = data.group_id

        # 2. Check conflicts
        has_conflict, conflict_code = member_repo.find_conflicts(
            db=db,
            national_id=data.national_id,
            mobile=data.mobile,
            email=data.email,
            exclude_id=member.id,
        )
        if has_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate entry detected: {conflict_code}",
            )

        # 3. Status tracking
        if data.status and data.status != member.status:
            history = MemberStatusHistory(
                memberId=member.id,
                fromStatus=member.status,
                toStatus=data.status,
                reason=data.remarks or "Status updated via API",
                changedBy=current_user_id,
            )
            db.add(history)
            member.status = data.status

        # 4. Update fields if provided
        if data.full_name is not None:
            member.fullName = data.full_name.strip()
        if data.father_name is not None:
            member.fatherName = data.father_name.strip() if data.father_name else None
        if data.mother_name is not None:
            member.motherName = data.mother_name.strip() if data.mother_name else None
        if data.gender is not None:
            member.gender = data.gender
        if data.dob is not None:
            member.dob = data.dob
        if data.national_id is not None:
            member.nationalId = data.national_id.strip() if data.national_id else None
        if data.id_document_type is not None:
            member.idDocumentType = data.id_document_type
        if data.occupation is not None:
            member.occupation = data.occupation.strip() if data.occupation else None
        if data.monthly_income is not None:
            member.monthlyIncome = data.monthly_income
        if data.blood_group is not None:
            member.bloodGroup = data.blood_group
        if data.mobile is not None:
            member.mobile = data.mobile.strip() if data.mobile else None
        if data.alt_mobile is not None:
            member.altMobile = data.alt_mobile.strip() if data.alt_mobile else None
        if data.email is not None:
            member.email = data.email.strip() if data.email else None
        if data.phone is not None:
            member.phone = data.phone.strip() if data.phone else None
        if data.present_address is not None:
            member.presentAddress = data.present_address.strip() if data.present_address else None
        if data.permanent_address is not None:
            member.permanentAddress = data.permanent_address.strip() if data.permanent_address else None
        if data.emergency_contact_name is not None:
            member.emergencyContactName = data.emergency_contact_name.strip() if data.emergency_contact_name else None
        if data.emergency_contact_mobile is not None:
            member.emergencyContactMobile = data.emergency_contact_mobile.strip() if data.emergency_contact_mobile else None
        if data.emergency_contact_relation is not None:
            member.emergencyContactRelation = data.emergency_contact_relation.strip() if data.emergency_contact_relation else None

        if data.reference is not None:
            member.reference = json.dumps({
                "name": data.reference.name or "",
                "mobile": data.reference.mobile or "",
                "relation": data.reference.relation or "",
            })
        elif data.reference_name or data.reference_mobile or data.reference_relation:
            member.reference = json.dumps({
                "name": data.reference_name or "",
                "mobile": data.reference_mobile or "",
                "relation": data.reference_relation or "",
            })

        if data.join_date is not None:
            member.joinDate = data.join_date
        if data.remarks is not None:
            member.remarks = data.remarks
        if data.marital_status is not None:
            member.maritalStatus = data.marital_status
        if data.education is not None:
            member.education = data.education
        if data.workplace is not None:
            member.workplace = data.workplace
        if data.designation is not None:
            member.designation = data.designation
        if data.skills is not None:
            member.skills = data.skills
        if data.reason_for_joining is not None:
            member.reasonForJoining = data.reason_for_joining
        if data.member_type is not None:
            member.memberType = data.member_type
        if data.position is not None:
            member.position = data.position

        member.updatedBy = current_user_id

        audit_repo.log(
            db=db,
            action="UPDATE",
            module="MEMBER",
            user_id=current_user_id,
            reference_id=member.id,
            remarks=f"Updated member {member.memberId}",
        )

        db.commit()
        db.refresh(member)
        return format_member_detail_response(member)

    def delete_member(
        self,
        db: Session,
        member_id: str,
        current_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        member = member_repo.get_by_id(db, member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member with ID '{member_id}' not found",
            )

        old_status = member.status
        member.status = "DELETED"
        member.updatedBy = current_user_id

        history = MemberStatusHistory(
            memberId=member.id,
            fromStatus=old_status,
            toStatus="DELETED",
            reason="Member deleted via API",
            changedBy=current_user_id,
        )
        db.add(history)

        audit_repo.log(
            db=db,
            action="DELETE",
            module="MEMBER",
            user_id=current_user_id,
            reference_id=member.id,
            remarks=f"Soft deleted member {member.memberId}",
        )

        db.commit()
        return {"status": "ok", "message": f"Member {member.memberId} soft-deleted successfully"}


member_service = MemberService()
