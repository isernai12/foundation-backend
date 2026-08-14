from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import engine, check_db_health
from app.core.errors import register_exception_handlers
from app.api.router import api_router
from app.schemas.common import HealthResponse, DatabaseHealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: configure safe logging
    setup_logging(log_level=settings.LOG_LEVEL, debug=settings.DEBUG)
    yield
    # Shutdown: cleanly dispose of database connection pools
    engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI Backend Foundation for Foundation ERP & Management System",
    version="0.1.0",
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    docs_url=f"{settings.API_V1_STR}/docs" if settings.DEBUG else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if settings.DEBUG else None,
)

# Exception handlers for safe, standardized error formatting
register_exception_handlers(app)

# CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Root Health Endpoints
@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    tags=["Health"],
)
def root_health() -> HealthResponse:
    """Basic health check endpoint returning status ok."""
    return HealthResponse(status="ok")


@app.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    summary="Database Health Check",
    tags=["Health"],
)
def root_database_health(response: Response) -> DatabaseHealthResponse:
    """Harmless read-only SELECT 1 check to verify PostgreSQL connectivity."""
    db_status = check_db_health()
    if db_status.get("status") != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return DatabaseHealthResponse(
            status=db_status.get("status", "error"),
            database=db_status.get("database", "disconnected"),
            detail=db_status.get("detail", "Database connection check failed"),
        )
    return DatabaseHealthResponse(status="ok", database="connected")


# Mount API Routers (/api/v1/...)
app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "environment": settings.ENVIRONMENT,
        "docs": f"{settings.API_V1_STR}/docs" if settings.DEBUG else None,
        "health": "/health",
        "health_db": "/health/db",
    }
