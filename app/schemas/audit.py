import datetime
from typing import Optional, List
from pydantic import BaseModel


class AuditLogUser(BaseModel):
    name: str
    username: str


class AuditLogItem(BaseModel):
    id: str
    userId: Optional[str] = None
    action: str
    module: str
    resourceId: Optional[str] = None
    oldData: Optional[str] = None
    newData: Optional[str] = None
    ipAddress: Optional[str] = None
    device: Optional[str] = None
    browser: Optional[str] = None
    remarks: Optional[str] = None
    createdAt: datetime.datetime
    user: Optional[AuditLogUser] = None
