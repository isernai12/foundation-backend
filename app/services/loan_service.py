import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.loan import Loan, LoanRepayment
from backend.app.models.member import Member
from backend.app.models.beneficiary import Beneficiary
from backend.app.schemas.loan import (
    QardHasanaCreateRequest,
    QardHasanaUpdateRequest,
    QardHasanaResponse,
    QardHasanaListResponse,
    RepaymentCreateRequest,
    RepaymentResponse,
    QardHasanaLedgerItem,
    QardHasanaLedgerResponse,
)
from backend.app.repositories import (
    loan_repo,
    member_repo,
    beneficiary_repo,
    fund_repo,
    group_repo,
    ledger_repo,
    audit_repo,
)


def format_loan_response(l: Loan) -> QardHasanaResponse:
    member_name = l.member.fullName if l.member else None
    beneficiary_name = l.beneficiary.fullName if l.beneficiary else None
    return QardHasanaResponse(
        id=l.id,
        loan_number=l.loanNumber,
        member_id=l.memberId,
        member_name=member_name,
        beneficiary_id=l.beneficiaryId,
        beneficiary_name=beneficiary_name,
        amount=l.amount,
        total_paid_amount=l.totalPaidAmount,
        remaining_balance=l.remainingBalance,
        loan_type=l.loanType,
        business_type=l.businessType,
        purpose=l.purpose,
        requested_date=l.requestedDate,
        disbursed_date=l.disbursedDate,
        status=l.status,
        installment_type=l.installmentType,
        installment_amount=l.installmentAmount,
        total_installments=l.totalInstallments,
        first_installment_date=l.firstInstallmentDate,
        next_due_date=l.nextDueDate,
        notes=l.notes,
        created_at=l.createdAt,
    )


class LoanService:
    def create_qard_hasana(
        self,
        db: Session,
        data: QardHasanaCreateRequest,
        current_user_id: Optional[str] = None,
    ) -> QardHasanaResponse:
        final_member_id: Optional[str] = None
        final_beneficiary_id: Optional[str] = None
        target_group_id: Optional[str] = data.group_id

        # 1. Recipient validation
        if data.member_id:
            member = member_repo.get_by_id(db, data.member_id)
            if not member:
                raise HTTPException(status_code=404, detail=f"Member '{data.member_id}' not found.")
            final_member_id = member.id
            if not target_group_id:
                target_group_id = member.groupId

        if data.beneficiary_id:
            beneficiary = beneficiary_repo.get_by_id(db, data.beneficiary_id)
            if not beneficiary:
                raise HTTPException(status_code=404, detail=f"Beneficiary '{data.beneficiary_id}' not found.")
            final_beneficiary_id = beneficiary.id
            if not target_group_id and beneficiary.member:
                target_group_id = beneficiary.member.groupId

        if not final_member_id and not final_beneficiary_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recipient must be specified (either member_id or beneficiary_id).",
            )

        loan_number = loan_repo.generate_next_loan_number(db)
        req_date = data.requested_date or datetime.datetime.now(datetime.timezone.utc)
        disb_date = datetime.datetime.now(datetime.timezone.utc)

        try:
            # 2. Resolve Funds
            group_fund, general_fund = fund_repo.get_or_create_funds(db, target_group_id)

            # 3. Create Balanced Ledger Transaction:
            # Debit: Group Fund (outflow allocation)
            # Credit: General Cash Fund (cash disbursed)
            entries = [
                {
                    "fundId": group_fund.id,
                    "isCredit": False,
                    "amount": data.amount,
                    "groupId": target_group_id,
                    "groupCode": group_fund.group.code if group_fund.group else None,
                    "groupName": group_fund.group.name if group_fund.group else None,
                },
                {"fundId": general_fund.id, "isCredit": True, "amount": data.amount},
            ]

            ref_str = final_member_id or final_beneficiary_id or loan_number
            tx = ledger_repo.create_balanced_transaction(
                db=db,
                date=disb_date,
                type="LOAN",
                reference_id=loan_number,
                member_id=final_member_id,
                donor_id=None,
                notes=f"Disbursed Qard-e-Hasana: {loan_number} ({data.purpose})",
                created_by=current_user_id,
                entries=entries,
            )

            # 4. Create Loan Entity
            loan = Loan(
                loanNumber=loan_number,
                memberId=final_member_id,
                beneficiaryId=final_beneficiary_id,
                amount=data.amount,
                loanType=data.loan_type,
                businessType=data.business_type if data.loan_type == "BUSINESS" else None,
                purpose=data.purpose.strip(),
                requestedDate=req_date,
                disbursedDate=disb_date,
                status="ACTIVE",
                notes=data.notes,
                installmentType=data.installment_type,
                installmentAmount=data.installment_amount,
                totalInstallments=data.total_installments,
                firstInstallmentDate=data.first_installment_date,
                nextDueDate=data.first_installment_date,
                totalPaidAmount=0,
                remainingBalance=data.amount,
                createdBy=current_user_id,
            )
            db.add(loan)
            db.flush()

            audit_repo.log(
                db=db,
                action="DISBURSE_LOAN",
                module="LOANS",
                user_id=current_user_id,
                reference_id=loan.id,
                remarks=f"Disbursed Qard-e-Hasana {loan.loanNumber} of ৳{loan.amount}",
            )

            db.commit()
            db.refresh(loan)
            return format_loan_response(loan)
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Qard-e-Hasana disbursement failed: {str(e)}")

    def get_qard_hasana(self, db: Session, loan_id: str) -> QardHasanaResponse:
        loan = loan_repo.get_by_id(db, loan_id)
        if not loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Qard-e-Hasana with ID '{loan_id}' not found",
            )
        return format_loan_response(loan)

    def list_qard_hasana(
        self,
        db: Session,
        query: Optional[str] = None,
        status_filter: Optional[str] = None,
        member_id: Optional[str] = None,
        beneficiary_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> QardHasanaListResponse:
        items, total = loan_repo.search_and_paginate(
            db=db,
            query=query,
            status_filter=status_filter,
            member_id=member_id,
            beneficiary_id=beneficiary_id,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return QardHasanaListResponse(
            items=[format_loan_response(l) for l in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def update_qard_hasana(
        self,
        db: Session,
        loan_id: str,
        data: QardHasanaUpdateRequest,
        current_user_id: Optional[str] = None,
    ) -> QardHasanaResponse:
        loan = loan_repo.get_by_id(db, loan_id)
        if not loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Qard-e-Hasana with ID '{loan_id}' not found",
            )

        if data.purpose is not None:
            loan.purpose = data.purpose.strip()
        if data.notes is not None:
            loan.notes = data.notes
        if data.installment_type is not None:
            loan.installmentType = data.installment_type
        if data.installment_amount is not None:
            loan.installmentAmount = data.installment_amount
        if data.total_installments is not None:
            loan.totalInstallments = data.total_installments
        if data.next_due_date is not None:
            loan.nextDueDate = data.next_due_date
        if data.status is not None:
            loan.status = data.status

        loan.updatedBy = current_user_id

        audit_repo.log(
            db=db,
            action="UPDATE",
            module="LOANS",
            user_id=current_user_id,
            reference_id=loan.id,
            remarks=f"Updated Qard-e-Hasana {loan.loanNumber}",
        )

        db.commit()
        db.refresh(loan)
        return format_loan_response(loan)

    def repay_qard_hasana(
        self,
        db: Session,
        loan_id: str,
        data: RepaymentCreateRequest,
        current_user_id: Optional[str] = None,
    ) -> RepaymentResponse:
        loan = loan_repo.get_by_id(db, loan_id)
        if not loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Qard-e-Hasana with ID '{loan_id}' not found",
            )
        if loan.status not in ["ACTIVE", "DEFAULTED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot record repayment for loan in '{loan.status}' status.",
            )

        # STRICT OVERPAYMENT CHECK
        if data.amount > loan.remainingBalance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Repayment amount (৳{data.amount}) exceeds remaining outstanding balance (৳{loan.remainingBalance}).",
            )

        pay_date = data.payment_date or datetime.datetime.now(datetime.timezone.utc)
        target_group_id = loan.member.groupId if loan.member else None

        try:
            # 1. Resolve Funds
            group_fund, general_fund = fund_repo.get_or_create_funds(db, target_group_id)

            # 2. Balanced Double-Entry:
            # Debit: General Cash Fund (cash in)
            # Credit: Group Fund (receivable recovered)
            entries = [
                {"fundId": general_fund.id, "isCredit": False, "amount": data.amount},
                {
                    "fundId": group_fund.id,
                    "isCredit": True,
                    "amount": data.amount,
                    "groupId": target_group_id,
                    "groupCode": group_fund.group.code if group_fund.group else None,
                    "groupName": group_fund.group.name if group_fund.group else None,
                },
            ]

            tx = ledger_repo.create_balanced_transaction(
                db=db,
                date=pay_date,
                type="LOAN_REPAYMENT",
                reference_id=data.reference_number or loan.loanNumber,
                member_id=loan.memberId,
                donor_id=None,
                notes=data.notes or f"Repayment for {loan.loanNumber}",
                created_by=current_user_id,
                entries=entries,
            )

            # 3. Create LoanRepayment
            repayment = LoanRepayment(
                loanId=loan.id,
                ledgerTransactionId=tx.id,
                amount=data.amount,
                date=pay_date,
                status="COMPLETED",
                installmentNo=data.installment_no,
                paymentMethod=data.payment_method,
                referenceNumber=data.reference_number,
                notes=data.notes,
                collectedBy=data.collected_by,
                createdBy=current_user_id,
            )
            db.add(repayment)

            # 4. Atomic Balance and Status Update
            loan.totalPaidAmount += data.amount
            loan.remainingBalance -= data.amount

            if loan.remainingBalance == 0:
                loan.status = "PAID"

            loan.updatedBy = current_user_id

            audit_repo.log(
                db=db,
                action="REPAY_LOAN",
                module="LOANS",
                user_id=current_user_id,
                reference_id=repayment.id,
                remarks=f"Received repayment ৳{data.amount} for {loan.loanNumber}. Remaining: ৳{loan.remainingBalance}",
            )

            db.commit()
            db.refresh(repayment)
            db.refresh(loan)

            return RepaymentResponse(
                id=repayment.id,
                loan_id=loan.id,
                amount=repayment.amount,
                date=repayment.date,
                status=repayment.status,
                installment_no=repayment.installmentNo,
                payment_method=repayment.paymentMethod,
                reference_number=repayment.referenceNumber,
                notes=repayment.notes,
                remaining_loan_balance=loan.remainingBalance,
                loan_status=loan.status,
                ledger_transaction_id=tx.id,
                created_at=repayment.createdAt,
            )
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Repayment transaction failed: {str(e)}")

    def get_qard_hasana_ledger(
        self,
        db: Session,
        loan_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> QardHasanaLedgerResponse:
        loan = loan_repo.get_by_id(db, loan_id)
        if not loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Qard-e-Hasana with ID '{loan_id}' not found",
            )

        entries = loan_repo.get_loan_ledger_entries(db, loan_id)
        recipient = (
            loan.member.fullName
            if loan.member
            else (loan.beneficiary.fullName if loan.beneficiary else "Unknown")
        )

        total = len(entries)
        offset = (page - 1) * page_size
        paged = entries[offset : offset + page_size]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        items = [
            QardHasanaLedgerItem(
                id=item["id"],
                date=item["date"],
                type=item["type"],
                amount=item["amount"],
                running_balance=item["running_balance"],
                payment_method=item["payment_method"],
                reference_number=item["reference_number"],
                notes=item["notes"],
                created_at=item["created_at"],
            )
            for item in paged
        ]

        return QardHasanaLedgerResponse(
            loan_id=loan.id,
            loan_number=loan.loanNumber,
            recipient_name=recipient,
            original_amount=loan.amount,
            total_repaid=loan.totalPaidAmount,
            current_balance=loan.remainingBalance,
            status=loan.status,
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


loan_service = LoanService()
