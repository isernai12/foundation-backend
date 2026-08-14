"""Services package."""
from backend.app.services.base import BaseService
from backend.app.services.member_service import MemberService, member_service
from backend.app.services.member_request_service import (
    MemberRequestService,
    member_request_service,
)
from backend.app.services.group_service import GroupService, group_service
from backend.app.services.fund_service import FundService, fund_service
from backend.app.services.sadaqah_service import SadaqahService, sadaqah_service
from backend.app.services.dues_service import DuesService, dues_service
from backend.app.services.financial_activity_service import (
    FinancialActivityService,
    financial_activity_service,
)
from backend.app.services.loan_service import LoanService, loan_service
from backend.app.services.beneficiary_service import (
    BeneficiaryService,
    beneficiary_service,
)
from backend.app.services.reports_service import (
    ReportsService,
    reports_service,
)

__all__ = [
    "BaseService",
    "MemberService",
    "member_service",
    "MemberRequestService",
    "member_request_service",
    "GroupService",
    "group_service",
    "FundService",
    "fund_service",
    "SadaqahService",
    "sadaqah_service",
    "DuesService",
    "dues_service",
    "FinancialActivityService",
    "financial_activity_service",
    "LoanService",
    "loan_service",
    "BeneficiaryService",
    "beneficiary_service",
    "ReportsService",
    "reports_service",
]
