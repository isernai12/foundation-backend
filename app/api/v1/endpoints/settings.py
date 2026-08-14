from typing import Dict, Optional, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.settings import SystemSettings, FoundationProfile
from app.models.auth import User
from app.rbac.dependencies import require_permission
from app.repositories import audit_repo

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get(
    "/system",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Get System Settings",
)
def get_system_settings(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("Settings", "View")),
) -> Dict[str, str]:
    stmt = select(SystemSettings)
    items = db.scalars(stmt).all()
    result: Dict[str, str] = {}
    for item in items:
        result[item.key] = item.value
    if "DEFAULT_MONTHLY_CONTRIBUTION" not in result and "membership.monthlyFee" not in result:
        result["DEFAULT_MONTHLY_CONTRIBUTION"] = "100"
        result["membership.monthlyFee"] = "100"
    return result


@router.post(
    "/system",
    response_model=Dict[str, bool],
    status_code=status.HTTP_200_OK,
    summary="Save System Settings",
)
def save_system_settings(
    settings_map: Dict[str, str],
    group: str = "General",
    current_user: User = Depends(require_permission("Settings", "Manage")),
    db: Session = Depends(get_db),
) -> Dict[str, bool]:
    updated_map = dict(settings_map)
    if "DEFAULT_MONTHLY_CONTRIBUTION" in updated_map:
        updated_map["membership.monthlyFee"] = updated_map["DEFAULT_MONTHLY_CONTRIBUTION"]
    elif "membership.monthlyFee" in updated_map:
        updated_map["DEFAULT_MONTHLY_CONTRIBUTION"] = updated_map["membership.monthlyFee"]

    for key, value in updated_map.items():
        stmt = select(SystemSettings).where(SystemSettings.key == key)
        existing = db.scalars(stmt).first()
        if existing:
            existing.value = str(value)
        else:
            new_setting = SystemSettings(key=key, value=str(value), group=group)
            db.add(new_setting)

    audit_repo.log(
        db,
        action="UPDATE",
        module="SETTINGS",
        user_id=current_user.id,
        remarks="Updated System Settings",
    )
    db.commit()
    return {"success": True}


@router.get(
    "/monthly-fee",
    response_model=Dict[str, int],
    status_code=status.HTTP_200_OK,
    summary="Get Default Monthly Membership Fee",
)
def get_monthly_fee(
    db: Session = Depends(get_db),
) -> Dict[str, int]:
    stmt = select(SystemSettings).where(
        SystemSettings.key.in_(["DEFAULT_MONTHLY_CONTRIBUTION", "membership.monthlyFee"])
    )
    settings = db.scalars(stmt).all()
    setting = next((s for s in settings if s.key == "DEFAULT_MONTHLY_CONTRIBUTION"), None) or next(
        (s for s in settings if s.key == "membership.monthlyFee"), None
    )
    if not setting or not setting.value:
        return {"fee": 100}
    try:
        fee = int(setting.value)
        return {"fee": fee if fee > 0 else 100}
    except Exception:
        return {"fee": 100}


@router.get(
    "/foundation-profile",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Foundation Profile",
)
def get_foundation_profile(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("Settings", "View")),
) -> Dict[str, Any]:
    stmt = select(FoundationProfile)
    profile = db.scalars(stmt).first()
    if not profile:
        return {
            "name": "Foundation Name",
            "email": "",
            "phone": "",
            "address": "",
            "website": "",
            "currency": "BDT",
        }
    return {
        "id": profile.id,
        "name": profile.name,
        "logo": profile.logo,
        "email": profile.email or "",
        "phone": profile.phone or "",
        "address": profile.address or "",
        "website": profile.website or "",
        "currency": profile.currency or "BDT",
    }


@router.post(
    "/foundation-profile",
    response_model=Dict[str, bool],
    status_code=status.HTTP_200_OK,
    summary="Save Foundation Profile",
)
def save_foundation_profile(
    data: Dict[str, Any],
    current_user: User = Depends(require_permission("Settings", "Manage")),
    db: Session = Depends(get_db),
) -> Dict[str, bool]:
    stmt = select(FoundationProfile)
    existing = db.scalars(stmt).first()
    if existing:
        for k, v in data.items():
            if hasattr(existing, k):
                setattr(existing, k, v)
    else:
        new_prof = FoundationProfile(name=data.get("name", "Foundation"), **{k: v for k, v in data.items() if k != "name"})
        db.add(new_prof)

    audit_repo.log(
        db,
        action="UPDATE",
        module="SETTINGS",
        user_id=current_user.id,
        remarks="Updated Foundation Profile",
    )
    db.commit()
    return {"success": True}
