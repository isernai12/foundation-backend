import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username or Email address")
    password: str = Field(..., description="Plaintext password")
    remember_me: bool = Field(default=False, description="Extend session duration to 30 days")


class RoleInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = None


class UserProfile(BaseModel):
    id: str
    name: str
    username: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    role: str
    status: str
    photo: Optional[str] = None
    preferences: Optional[str] = None
    permissions: List[str] = []


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # in seconds
    user: UserProfile


class SessionInfo(BaseModel):
    id: str
    jti: str
    device: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    ip_address: Optional[str] = None
    last_active: datetime.datetime
    expires_at: datetime.datetime


class LogoutResponse(BaseModel):
    status: str = "ok"
    message: str = "Successfully logged out"
