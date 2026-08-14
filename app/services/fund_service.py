from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.fund import Fund
from app.schemas.fund import (
    FundCreateRequest,
    FundUpdateRequest,
    FundResponse,
    FundListResponse,
)
from app.repositories import fund_repo, group_repo, audit_repo


def format_fund_response(f: Fund, db: Session) -> FundResponse:
    balance = fund_repo.get_fund_balance(db, f.id)
    return FundResponse(
        id=f.id,
        group_id=f.groupId,
        group_name=f.group.name if f.group else "General Foundation Fund",
        group_code=f.group.code if f.group else "HQ",
        name=f.name,
        description=f.description,
        current_balance=balance,
        created_at=f.createdAt,
        updated_at=f.updatedAt,
    )


class FundService:
    def list_funds(
        self,
        db: Session,
        query: Optional[str] = None,
        group_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> FundListResponse:
        # Ensure root General Fund exists
        fund_repo.get_general_fund(db)

        items, total = fund_repo.search_and_paginate(
            db=db,
            query=query,
            group_id=group_id,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return FundListResponse(
            items=[format_fund_response(f, db) for f in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_fund(self, db: Session, fund_id: str) -> FundResponse:
        fund = fund_repo.get_by_id(db, fund_id)
        if not fund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fund with ID '{fund_id}' not found",
            )
        return format_fund_response(fund, db)

    def create_fund(
        self,
        db: Session,
        data: FundCreateRequest,
        current_user_id: Optional[str] = None,
    ) -> FundResponse:
        if data.group_id:
            group = group_repo.get_by_id(db, data.group_id)
            if not group:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target group '{data.group_id}' does not exist.",
                )

        fund = Fund(
            groupId=data.group_id,
            name=data.name.strip(),
            description=data.description,
            createdBy=current_user_id,
        )
        db.add(fund)
        db.flush()

        audit_repo.log(
            db=db,
            action="CREATE",
            module="FUND",
            user_id=current_user_id,
            reference_id=fund.id,
            remarks=f"Created fund {fund.name}",
        )

        db.commit()
        db.refresh(fund)
        return format_fund_response(fund, db)

    def update_fund(
        self,
        db: Session,
        fund_id: str,
        data: FundUpdateRequest,
        current_user_id: Optional[str] = None,
    ) -> FundResponse:
        fund = fund_repo.get_by_id(db, fund_id)
        if not fund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fund with ID '{fund_id}' not found",
            )

        if data.group_id is not None and data.group_id != fund.groupId:
            group = group_repo.get_by_id(db, data.group_id)
            if not group:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target group '{data.group_id}' does not exist.",
                )
            fund.groupId = data.group_id

        if data.name is not None:
            fund.name = data.name.strip()
        if data.description is not None:
            fund.description = data.description

        fund.updatedBy = current_user_id

        audit_repo.log(
            db=db,
            action="UPDATE",
            module="FUND",
            user_id=current_user_id,
            reference_id=fund.id,
            remarks=f"Updated fund {fund.name}",
        )

        db.commit()
        db.refresh(fund)
        return format_fund_response(fund, db)


fund_service = FundService()
