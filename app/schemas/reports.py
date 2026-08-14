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


class MonthlyChartItem(BaseModel):
    month: str
    contributions: int = 0
    loans: int = 0
    grants: int = 0


class GroupDistributionItem(BaseModel):
    name: str
    value: int = 0


class DashboardStatsResponse(BaseModel):
    totalMembers: int = 0
    activeMembers: int = 0
    inactiveMembers: int = 0
    totalGroups: int = 0
    foundationTotalFund: int = 0
    totalGroupFunds: int = 0
    currentCashBalance: int = 0
    totalContributions: int = 0
    totalActiveLoans: int = 0
    outstandingLoanAmount: int = 0
    totalGrants: int = 0
    totalBeneficiaries: int = 0
    groupFundDistribution: List[GroupDistributionItem] = []
    monthlyChartData: List[MonthlyChartItem] = []
