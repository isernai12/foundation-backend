"""Repositories package."""
from app.repositories.base import BaseRepository
from app.repositories.user_repo import UserRepository, user_repo
from app.repositories.role_repo import RoleRepository, role_repo
from app.repositories.session_repo import SessionRepository, session_repo
from app.repositories.audit_repo import AuditLogRepository, audit_repo
from app.repositories.group_repo import GroupRepository, group_repo
from app.repositories.member_repo import MemberRepository, member_repo
from app.repositories.member_request_repo import (
    MemberRequestRepository,
    member_request_repo,
)
from app.repositories.fund_repo import FundRepository, fund_repo
from app.repositories.donor_repo import DonorRepository, donor_repo
from app.repositories.ledger_repo import LedgerRepository, ledger_repo
from app.repositories.settings_repo import SettingsRepository, settings_repo
from app.repositories.contribution_repo import (
    ContributionRepository,
    contribution_repo,
)
from app.repositories.beneficiary_repo import (
    BeneficiaryRepository,
    beneficiary_repo,
)
from app.repositories.campaign_repo import (
    CampaignRepository,
    campaign_repo,
)
from app.repositories.loan_repo import (
    LoanRepository,
    loan_repo,
)

__all__ = [
    "BaseRepository",
    "UserRepository",
    "user_repo",
    "RoleRepository",
    "role_repo",
    "SessionRepository",
    "session_repo",
    "AuditLogRepository",
    "audit_repo",
    "GroupRepository",
    "group_repo",
    "MemberRepository",
    "member_repo",
    "MemberRequestRepository",
    "member_request_repo",
    "FundRepository",
    "fund_repo",
    "DonorRepository",
    "donor_repo",
    "LedgerRepository",
    "ledger_repo",
    "SettingsRepository",
    "settings_repo",
    "ContributionRepository",
    "contribution_repo",
    "BeneficiaryRepository",
    "beneficiary_repo",
    "CampaignRepository",
    "campaign_repo",
    "LoanRepository",
    "loan_repo",
]
