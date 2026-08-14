from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.organization import Group
from app.schemas.group import (
    GroupCreateRequest,
    GroupUpdateRequest,
    GroupResponse,
    GroupListResponse,
)
from app.repositories import group_repo, audit_repo


def format_group_response(g: Group, db: Session) -> GroupResponse:
    member_count = group_repo.get_member_count(db, g.id)
    current_balance = group_repo.get_group_balance(db, g.id)
    return GroupResponse(
        id=g.id,
        foundation_id=g.foundationId,
        name=g.name,
        code=g.code,
        short_name=g.shortName,
        description=g.description,
        remarks=g.remarks,
        status=g.status,
        is_foundation_group=g.isFoundationGroup,
        member_signup_enabled=g.memberSignupEnabled,
        member_count=member_count,
        current_balance=current_balance,
        created_at=g.createdAt,
        updated_at=g.updatedAt,
    )


class GroupService:
    def list_groups(
        self,
        db: Session,
        query: Optional[str] = None,
        status_filter: Optional[str] = None,
        signup_enabled: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> GroupListResponse:
        # Ensure the special foundation group is seeded
        group_repo.ensure_foundation_group(db)

        items, total = group_repo.search_and_paginate(
            db=db,
            query=query,
            status_filter=status_filter,
            member_signup_enabled=signup_enabled,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return GroupListResponse(
            items=[format_group_response(g, db) for g in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_group(self, db: Session, group_id: str) -> GroupResponse:
        group = group_repo.get_by_id(db, group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group with ID '{group_id}' not found",
            )
        return format_group_response(group, db)

    def create_group(
        self,
        db: Session,
        data: GroupCreateRequest,
        current_user_id: Optional[str] = None,
    ) -> GroupResponse:
        # 1. Foundation Group uniqueness
        if data.is_foundation_group:
            existing_fg = group_repo.get_foundation_group(db)
            if existing_fg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only one Foundation Central Group can exist in the system.",
                )

        # 2. Check unique code
        existing_code = group_repo.get_by_code(db, data.code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Group code '{data.code}' is already in use.",
            )

        # 3. Foundation Group rule: memberSignupEnabled must be False
        signup_enabled = False if data.is_foundation_group else data.member_signup_enabled

        foundation_id = data.foundation_id
        if not foundation_id:
            fg = group_repo.ensure_foundation_group(db)
            foundation_id = fg.foundationId

        group = Group(
            foundationId=foundation_id,
            name=data.name.strip(),
            code=data.code.strip().upper(),
            shortName=data.short_name.strip() if data.short_name else None,
            description=data.description,
            remarks=data.remarks,
            status=data.status or "ACTIVE",
            isFoundationGroup=data.is_foundation_group,
            memberSignupEnabled=signup_enabled,
            createdBy=current_user_id,
        )
        db.add(group)
        db.flush()

        audit_repo.log(
            db=db,
            action="CREATE",
            module="GROUP",
            user_id=current_user_id,
            reference_id=group.id,
            remarks=f"Created group {group.code} ({group.name})",
        )

        db.commit()
        db.refresh(group)
        return format_group_response(group, db)

    def update_group(
        self,
        db: Session,
        group_id: str,
        data: GroupUpdateRequest,
        current_user_id: Optional[str] = None,
    ) -> GroupResponse:
        group = group_repo.get_by_id(db, group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group with ID '{group_id}' not found",
            )

        # Code uniqueness check
        if data.code and data.code.strip().upper() != group.code:
            existing_code = group_repo.get_by_code(db, data.code)
            if existing_code and existing_code.id != group.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Group code '{data.code}' is already taken.",
                )
            group.code = data.code.strip().upper()

        if data.name is not None:
            group.name = data.name.strip()
        if data.short_name is not None:
            group.shortName = data.short_name.strip() if data.short_name else None
        if data.description is not None:
            group.description = data.description
        if data.remarks is not None:
            group.remarks = data.remarks
        if data.status is not None:
            group.status = data.status

        # Foundation Group rule: cannot enable member signup on the root foundation group
        if data.member_signup_enabled is not None:
            if group.isFoundationGroup and data.member_signup_enabled:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Member registration cannot be enabled on the root Foundation Central Group.",
                )
            group.memberSignupEnabled = data.member_signup_enabled

        group.updatedBy = current_user_id

        audit_repo.log(
            db=db,
            action="UPDATE",
            module="GROUP",
            user_id=current_user_id,
            reference_id=group.id,
            remarks=f"Updated group {group.code}",
        )

        db.commit()
        db.refresh(group)
        return format_group_response(group, db)


group_service = GroupService()
