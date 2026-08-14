from fastapi import APIRouter
from app.api.v1.endpoints import health
from app.auth.router import router as auth_router
from app.api.v1.endpoints.members import router as members_router
from app.api.v1.endpoints.member_requests import router as member_requests_router
from app.api.v1.endpoints.groups import router as groups_router
from app.api.v1.endpoints.funds import router as funds_router
from app.api.v1.endpoints.sadaqah import router as sadaqah_router
from app.api.v1.endpoints.dues import router as dues_router
from app.api.v1.endpoints.financial_activities import router as financial_activities_router
from app.api.v1.endpoints.qard_hasana import router as qard_hasana_router
from app.api.v1.endpoints.beneficiaries import router as beneficiaries_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.roles import router as roles_router
from app.api.v1.endpoints.permissions import router as permissions_router

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(members_router)
api_v1_router.include_router(member_requests_router)
api_v1_router.include_router(groups_router)
api_v1_router.include_router(funds_router)
api_v1_router.include_router(sadaqah_router)
api_v1_router.include_router(dues_router)
api_v1_router.include_router(financial_activities_router)
api_v1_router.include_router(qard_hasana_router)
api_v1_router.include_router(beneficiaries_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(roles_router)
api_v1_router.include_router(permissions_router)
