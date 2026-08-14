import datetime
from typing import List, Optional
from pydantic import BaseModel


class FinancialDomainSummary(BaseModel):
    monthly_dues_total: int = 0
    sadaqah_total: int = 0
    financial_activities_income: int = 0
    financial_activities_disbursed: int = 0
    financial_activities_balance: int = 0
    qard_hasana_disbursed: int = 0
    qard_hasana_repaid: int = 0
    qard_hasana_outstanding: int = 0
    total_liquid_funds: int = 0


class GroupFinancialSummaryItem(BaseModel):
    group_id: str
    group_code: str
    group_name: str
    is_foundation_group: bool
    member_count: int
    dues_collected: int
    sadaqah_collected: int
    qard_hasana_disbursed: int
    qard_hasana_repaid: int
    current_balance: int


class FinancialReportSummaryResponse(BaseModel):
    generated_at: datetime.datetime
    overall: FinancialDomainSummary
    groups: List[GroupFinancialSummaryItem]
