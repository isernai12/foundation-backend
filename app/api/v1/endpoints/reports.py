from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.auth import User
from app.schemas.reports import FinancialReportSummaryResponse, DashboardStatsResponse
from app.services.reports_service import reports_service
from app.rbac.dependencies import require_permission

router = APIRouter(prefix="/reports", tags=["Financial Reports"])


@router.get(
    "/summary",
    response_model=FinancialReportSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Financial Domain Summary Report",
    description="Retrieves a consolidated breakdown across Monthly Dues, Sadaqah, Financial Activities, Qard-e-Hasana, and Group Fund balances.",
)
def get_financial_summary(
    current_user: User = Depends(require_permission("Reports", "View")),
    db: Session = Depends(get_db),
) -> FinancialReportSummaryResponse:
    return reports_service.get_financial_summary(db=db)


@router.get(
    "/dashboard-stats",
    response_model=DashboardStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Dashboard Aggregated Statistics",
    description="Retrieves consolidated KPIs, member counts, loan balances, group fund distribution, and 6-month financial trends.",
)
def get_dashboard_stats(
    db: Session = Depends(get_db),
) -> DashboardStatsResponse:
    return reports_service.get_dashboard_stats(db=db)
