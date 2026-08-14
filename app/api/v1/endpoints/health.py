from fastapi import APIRouter, status, Response
from backend.app.schemas.common import HealthResponse, DatabaseHealthResponse
from backend.app.core.database import check_db_health

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns simple ok status indicating the API process is alive.",
    tags=["Health"],
)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    summary="Database Health Check",
    description="Executes a read-only query (SELECT 1) to verify database connectivity without leaking credentials.",
    tags=["Health"],
)
def database_health_check(response: Response) -> DatabaseHealthResponse:
    db_status = check_db_health()
    if db_status.get("status") != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return DatabaseHealthResponse(
            status=db_status.get("status", "error"),
            database=db_status.get("database", "disconnected"),
            detail=db_status.get("detail", "Database connection check failed"),
        )

    return DatabaseHealthResponse(
        status="ok",
        database="connected",
    )
