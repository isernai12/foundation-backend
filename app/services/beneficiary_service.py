import datetime
from typing import Optional, List
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from backend.app.models.beneficiary import Beneficiary
from backend.app.models.member import Member
from backend.app.schemas.beneficiary import (
    BeneficiaryCreateRequest,
    BeneficiaryUpdateRequest,
    BeneficiaryResponse,
    BeneficiaryListResponse,
)
from backend.app.repositories import beneficiary_repo, member_repo, audit_repo


def format_beneficiary_response(b: Beneficiary) -> BeneficiaryResponse:
    member_name = b.member.fullName if b.member else None
    return BeneficiaryResponse(
        id=b.id,
        beneficiary_id=b.beneficiaryId,
        member_id=b.memberId,
        member_name=member_name,
        full_name=b.fullName,
        mobile=b.mobile,
        phone=b.phone,
        email=b.email,
        address=b.address or b.presentAddress,
        national_id=b.nationalId,
        father_or_husband_name=b.fatherOrHusbandName,
        occupation=b.occupation,
        remarks=b.remarks,
        relation_to_member=b.relationToMember,
        assistance_type=b.assistanceType,
        status=b.status,
        created_at=b.createdAt,
    )


class BeneficiaryService:
    def list_beneficiaries(
        self,
        db: Session,
        query: Optional[str] = None,
        status_filter: Optional[str] = None,
        member_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> BeneficiaryListResponse:
        stmt = select(Beneficiary).options(joinedload(Beneficiary.member))
        filters = []

        if status_filter:
            filters.append(Beneficiary.status == status_filter)

        if member_id:
            filters.append(Beneficiary.memberId == member_id)

        if query and query.strip():
            search = f"%{query.strip()}%"
            filters.append(
                or_(
                    Beneficiary.fullName.ilike(search),
                    Beneficiary.beneficiaryId.ilike(search),
                    Beneficiary.mobile.ilike(search),
                    Beneficiary.nationalId.ilike(search),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        stmt = stmt.order_by(Beneficiary.createdAt.desc())
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        items = list(db.scalars(stmt).unique().all())
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return BeneficiaryListResponse(
            items=[format_beneficiary_response(b) for b in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_beneficiary(self, db: Session, beneficiary_id: str) -> BeneficiaryResponse:
        b = beneficiary_repo.get_by_id(db, beneficiary_id)
        if not b:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Beneficiary with ID '{beneficiary_id}' not found",
            )
        return format_beneficiary_response(b)

    def create_beneficiary(
        self,
        db: Session,
        data: BeneficiaryCreateRequest,
        current_user_id: Optional[str] = None,
    ) -> BeneficiaryResponse:
        if data.member_id:
            member = member_repo.get_by_id(db, data.member_id)
            if not member:
                raise HTTPException(status_code=404, detail=f"Linked member '{data.member_id}' not found.")

        new_code = beneficiary_repo.generate_next_beneficiary_id(db)

        b = Beneficiary(
            beneficiaryId=new_code,
            fullName=data.full_name.strip(),
            memberId=data.member_id,
            mobile=data.mobile.strip() if data.mobile else None,
            phone=data.phone.strip() if data.phone else None,
            email=data.email.strip() if data.email else None,
            address=data.address,
            nationalId=data.national_id.strip() if data.national_id else None,
            fatherOrHusbandName=data.father_or_husband_name,
            occupation=data.occupation,
            remarks=data.remarks,
            relationToMember=data.relation_to_member,
            assistanceType=data.assistance_type,
            status=data.status or "ACTIVE",
            createdBy=current_user_id,
        )
        db.add(b)
        db.flush()

        audit_repo.log(
            db=db,
            action="CREATE",
            module="BENEFICIARIES",
            user_id=current_user_id,
            reference_id=b.id,
            remarks=f"Created Beneficiary {b.beneficiaryId} ({b.fullName})",
        )

        db.commit()
        db.refresh(b)
        return format_beneficiary_response(b)

    def update_beneficiary(
        self,
        db: Session,
        beneficiary_id: str,
        data: BeneficiaryUpdateRequest,
        current_user_id: Optional[str] = None,
    ) -> BeneficiaryResponse:
        b = beneficiary_repo.get_by_id(db, beneficiary_id)
        if not b:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Beneficiary with ID '{beneficiary_id}' not found",
            )

        if data.full_name is not None:
            b.fullName = data.full_name.strip()
        if data.member_id is not None:
            b.memberId = data.member_id
        if data.mobile is not None:
            b.mobile = data.mobile.strip() if data.mobile else None
        if data.phone is not None:
            b.phone = data.phone.strip() if data.phone else None
        if data.email is not None:
            b.email = data.email.strip() if data.email else None
        if data.address is not None:
            b.address = data.address
        if data.national_id is not None:
            b.nationalId = data.national_id.strip() if data.national_id else None
        if data.father_or_husband_name is not None:
            b.fatherOrHusbandName = data.father_or_husband_name
        if data.occupation is not None:
            b.occupation = data.occupation
        if data.remarks is not None:
            b.remarks = data.remarks
        if data.relation_to_member is not None:
            b.relationToMember = data.relation_to_member
        if data.assistance_type is not None:
            b.assistanceType = data.assistance_type
        if data.status is not None:
            b.status = data.status

        b.updatedBy = current_user_id

        audit_repo.log(
            db=db,
            action="UPDATE",
            module="BENEFICIARIES",
            user_id=current_user_id,
            reference_id=b.id,
            remarks=f"Updated Beneficiary {b.beneficiaryId}",
        )

        db.commit()
        db.refresh(b)
        return format_beneficiary_response(b)


beneficiary_service = BeneficiaryService()
