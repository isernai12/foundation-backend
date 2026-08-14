from typing import Optional
from pydantic import BaseModel, Field


class MediaUploadResponse(BaseModel):
    success: bool = True
    secure_url: str = Field(..., description="HTTPS CDN URL of the uploaded asset")
    public_id: str = Field(..., description="Cloudinary unique public identifier")
    format: Optional[str] = Field(None, description="File format/extension (e.g. jpg, png, pdf)")
    bytes: Optional[int] = Field(None, description="File size in bytes")
    resource_type: Optional[str] = Field(None, description="Resource type: image, raw, video")
    original_filename: Optional[str] = Field(None, description="Original uploaded filename")


class Base64UploadRequest(BaseModel):
    data: str = Field(..., description="Base64 encoded file string or data URI")
    folder: Optional[str] = Field(None, description="Target Cloudinary subfolder")
    filename: Optional[str] = Field(None, description="Optional original filename hint")


class MediaDeleteResponse(BaseModel):
    success: bool = True
    message: str
    result: Optional[str] = None
