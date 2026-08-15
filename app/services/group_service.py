from typing import Optional, List, Dict, Any
from sqlalchemy import select, delete, update, or_
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.organization import Group
from app.models.member import Member, MemberStatusHistory
from app.models.fund import Fund
from app.models.loan import Loan, LoanRepayment
from app.models.contribution import MonthlyContribution, ContributionPayment
from app.models.ledger import LedgerEntry, LedgerTransaction
from app.models.document import Document
from app.models.member_request import MemberRequest
from app.models.beneficiary import Beneficiary
from app.models.campaign import CampaignContribution
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
        try:
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
        except Exception:
            db.rollback()
            raise

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

        try:
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
        except Exception:
            db.rollback()
            raise

    def hard_delete_group(
        self,
        db: Session,
        group_id: str,
        current_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        group = group_repo.get_by_id(db, group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group with ID '{group_id}' not found",
            )

        if group.isFoundationGroup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The root Foundation Central Group cannot be deleted.",
            )

        group_code = group.code
        group_name = group.name

        try:
            # 1. Collect all member IDs belonging to this group
            stmt_members = select(Member.id).where(Member.groupId == group_id)
            member_ids = list(db.scalars(stmt_members).all())

            # 2. Collect all fund IDs belonging to this group
            stmt_funds = select(Fund.id).where(Fund.groupId == group_id)
            fund_ids = list(db.scalars(stmt_funds).all())

            # 3. Collect loan IDs belonging to these members
            loan_ids: List[str] = []
            if member_ids:
                stmt_loans = select(Loan.id).where(Loan.memberId.in_(member_ids))
                loan_ids = list(db.scalars(stmt_loans).all())

            # 4. Collect monthly contribution IDs for these members
            contribution_ids: List[str] = []
            if member_ids:
                stmt_contribs = select(MonthlyContribution.id).where(MonthlyContribution.memberId.in_(member_ids))
                contribution_ids = list(db.scalars(stmt_contribs).all())

            # 5. Collect ledger transaction IDs
            # A) from ContributionPayment
            tx_from_contribs: List[str] = []
            if contribution_ids:
                stmt_cp_tx = select(ContributionPayment.ledgerTransactionId).where(
                    ContributionPayment.monthlyContributionId.in_(contribution_ids)
                )
                tx_from_contribs = list(db.scalars(stmt_cp_tx).all())

            # B) from LoanRepayment
            tx_from_loans: List[str] = []
            if loan_ids:
                stmt_lr_tx = select(LoanRepayment.ledgerTransactionId).where(
                    LoanRepayment.loanId.in_(loan_ids)
                )
                tx_from_loans = list(db.scalars(stmt_lr_tx).all())

            # C) from LedgerTransaction directly tied to members
            tx_from_members: List[str] = []
            if member_ids:
                stmt_mem_tx = select(LedgerTransaction.id).where(
                    LedgerTransaction.memberId.in_(member_ids)
                )
                tx_from_members = list(db.scalars(stmt_mem_tx).all())

            # D) from LedgerEntry tied to group or group's funds
            tx_from_entries: List[str] = []
            entry_conditions = [LedgerEntry.groupId == group_id]
            if fund_ids:
                entry_conditions.append(LedgerEntry.fundId.in_(fund_ids))
            stmt_entry_tx = select(LedgerEntry.transactionId).where(or_(*entry_conditions))
            tx_from_entries = list(db.scalars(stmt_entry_tx).all())

            all_tx_ids = list(set(tx_from_contribs + tx_from_loans + tx_from_members + tx_from_entries))

            # --- DELETION IN DEPENDENCY ORDER (CHILDREN FIRST) ---

            # a. ContributionPayment
            if contribution_ids or all_tx_ids:
                cp_filters = []
                if contribution_ids:
                    cp_filters.append(ContributionPayment.monthlyContributionId.in_(contribution_ids))
                if all_tx_ids:
                    cp_filters.append(ContributionPayment.ledgerTransactionId.in_(all_tx_ids))
                if cp_filters:
                    stmt_del_cp = delete(ContributionPayment).where(or_(*cp_filters))
                    db.execute(stmt_del_cp)

            # b. LoanRepayment
            if loan_ids or all_tx_ids:
                lr_filters = []
                if loan_ids:
                    lr_filters.append(LoanRepayment.loanId.in_(loan_ids))
                if all_tx_ids:
                    lr_filters.append(LoanRepayment.ledgerTransactionId.in_(all_tx_ids))
                if lr_filters:
                    stmt_del_lr = delete(LoanRepayment).where(or_(*lr_filters))
                    db.execute(stmt_del_lr)

            # c. Disassociate / unlink Beneficiaries and CampaignContributions from deleted members
            if member_ids:
                stmt_un_ben = update(Beneficiary).where(Beneficiary.memberId.in_(member_ids)).values(memberId=None)
                db.execute(stmt_un_ben)

                stmt_un_cc = update(CampaignContribution).where(CampaignContribution.memberId.in_(member_ids)).values(memberId=None)
                db.execute(stmt_un_cc)

            # e. LedgerEntry (entries tied to this group, funds of this group, or transactions of this group)
            ledger_entry_filters = [LedgerEntry.groupId == group_id]
            if fund_ids:
                ledger_entry_filters.append(LedgerEntry.fundId.in_(fund_ids))
            if all_tx_ids:
                ledger_entry_filters.append(LedgerEntry.transactionId.in_(all_tx_ids))

            stmt_del_le = delete(LedgerEntry).where(or_(*ledger_entry_filters))
            db.execute(stmt_del_le)

            # f. LedgerTransaction
            if all_tx_ids:
                stmt_del_lt = delete(LedgerTransaction).where(LedgerTransaction.id.in_(all_tx_ids))
                db.execute(stmt_del_lt)

            # g. Loan
            if loan_ids:
                stmt_del_loans = delete(Loan).where(Loan.id.in_(loan_ids))
                db.execute(stmt_del_loans)

            # h. MonthlyContribution
            if contribution_ids:
                stmt_del_mc = delete(MonthlyContribution).where(MonthlyContribution.id.in_(contribution_ids))
                db.execute(stmt_del_mc)

            # i. MemberStatusHistory
            if member_ids:
                stmt_del_msh = delete(MemberStatusHistory).where(MemberStatusHistory.memberId.in_(member_ids))
                db.execute(stmt_del_msh)

            # j. Document
            doc_filters = [Document.groupId == group_id]
            if member_ids:
                doc_filters.append(Document.memberId.in_(member_ids))

            stmt_del_doc = delete(Document).where(or_(*doc_filters))
            db.execute(stmt_del_doc)

            # k. MemberRequest (applications associated with this group)
            stmt_del_mr = delete(MemberRequest).where(MemberRequest.groupId == group_id)
            db.execute(stmt_del_mr)

            # l. Member
            if member_ids:
                stmt_del_mem = delete(Member).where(Member.id.in_(member_ids))
                db.execute(stmt_del_mem)

            # m. Fund
            if fund_ids:
                stmt_del_fund = delete(Fund).where(Fund.id.in_(fund_ids))
                db.execute(stmt_del_fund)

            # n. Group
            stmt_del_grp = delete(Group).where(Group.id == group_id)
            db.execute(stmt_del_grp)

            # o. Audit Log
            audit_repo.log(
                db=db,
                action="HARD_DELETE",
                module="GROUP",
                user_id=current_user_id,
                reference_id=group_id,
                remarks=f"Permanently deleted group {group_code} ({group_name}) and all associated records ({len(member_ids)} members, {len(fund_ids)} funds, {len(loan_ids)} loans)",
            )

            db.commit()
            return {
                "success": True,
                "message": f"Group '{group_name}' ({group_code}) and all related records have been permanently deleted.",
                "deleted_group_id": group_id,
                "deleted_members_count": len(member_ids),
                "deleted_funds_count": len(fund_ids),
            }
        except Exception:
            db.rollback()
            raise


group_service = GroupService()
