import uuid
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.auth import User, Role, Permission, UserPermission
from app.auth.security import get_password_hash
from app.rbac.dependencies import require_permission
from app.repositories import audit_repo
from pydantic import BaseModel, Field

router = APIRouter(prefix="/users", tags=["User Management"])


class UserItemResponse(BaseModel):
    id: str
    name: str
    username: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    roleId: Optional[str] = None
    role: Optional[Dict[str, Any]] = None
    status: str
    photo: Optional[str] = None


class UserCreateRequest(BaseModel):
    name: str
    username: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    password: str
    roleId: str
    status: str = "ACTIVE"


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    password: Optional[str] = None
    roleId: Optional[str] = None
    status: Optional[str] = None


class UserPermissionsUpdateRequest(BaseModel):
    permissionIds: List[str]


@router.get("", response_model=List[Dict[str, Any]])
def list_users(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("Users", "View")),
):
    stmt = select(User).options(joinedload(User.role)).order_by(User.createdAt.desc())
    users = db.scalars(stmt).unique().all()
    results = []
    for u in users:
        results.append({
            "id": u.id,
            "name": u.name,
            "username": u.username,
            "email": u.email,
            "mobile": u.mobile,
            "roleId": u.roleId,
            "role": {"id": u.role.id, "name": u.role.name} if u.role else None,
            "status": u.status,
            "photo": u.photo,
        })
    return results


@router.get("/{user_id}", response_model=Dict[str, Any])
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("Users", "View")),
):
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(
            joinedload(User.role),
            joinedload(User.userPermissions).joinedload(UserPermission.permission),
        )
    )
    u = db.scalars(stmt).unique().first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {
        "id": u.id,
        "name": u.name,
        "username": u.username,
        "email": u.email,
        "mobile": u.mobile,
        "roleId": u.roleId,
        "role": {"id": u.role.id, "name": u.role.name} if u.role else None,
        "status": u.status,
        "photo": u.photo,
        "userPermissions": [
            {
                "permissionId": up.permissionId,
                "permission": {
                    "id": up.permission.id,
                    "module": up.permission.module,
                    "action": up.permission.action,
                } if up.permission else None,
            }
            for up in u.userPermissions
        ],
    }


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreateRequest,
    current_user: User = Depends(require_permission("Users", "Manage")),
    db: Session = Depends(get_db),
):
    # Check duplicate username
    stmt = select(User).where(User.username == data.username.strip())
    if db.scalars(stmt).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    hashed_password = get_password_hash(data.password)
    user = User(
        name=data.name.strip(),
        username=data.username.strip(),
        email=data.email.strip() if data.email else None,
        mobile=data.mobile.strip() if data.mobile else None,
        password=hashed_password,
        roleId=data.roleId,
        status=data.status,
    )
    db.add(user)
    audit_repo.log(
        db,
        action="CREATE",
        module="USER",
        user_id=current_user.id,
        remarks=f"Created user {user.username}",
    )
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "username": user.username}


@router.patch("/{user_id}", response_model=Dict[str, Any])
def update_user(
    user_id: str,
    data: UserUpdateRequest,
    current_user: User = Depends(require_permission("Users", "Manage")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if data.name is not None:
        user.name = data.name.strip()
    if data.username is not None:
        user.username = data.username.strip()
    if data.email is not None:
        user.email = data.email.strip() or None
    if data.mobile is not None:
        user.mobile = data.mobile.strip() or None
    if data.roleId is not None:
        user.roleId = data.roleId
    if data.status is not None:
        user.status = data.status
    if data.password:
        user.password = get_password_hash(data.password)

    audit_repo.log(
        db,
        action="UPDATE",
        module="USER",
        user_id=current_user.id,
        remarks=f"Updated user {user.username}",
    )
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "username": user.username}


@router.post("/{user_id}/permissions", response_model=Dict[str, bool])
def update_user_permissions(
    user_id: str,
    data: UserPermissionsUpdateRequest,
    current_user: User = Depends(require_permission("Users", "Manage")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Delete existing
    db.execute(delete(UserPermission).where(UserPermission.userId == user_id))

    # Add new
    for p_id in data.permissionIds:
        up = UserPermission(userId=user_id, permissionId=p_id)
        db.add(up)

    audit_repo.log(
        db,
        action="UPDATE_PERMISSIONS",
        module="USER",
        user_id=current_user.id,
        remarks=f"Updated permissions for user {user.username}",
    )
    db.commit()
    return {"success": True}
