from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from app.models.auth import User
from app.auth.dependencies import extract_token_from_request
from app.rbac.dependencies import require_authenticated_user
from app.schemas.media import MediaUploadResponse, Base64UploadRequest, MediaDeleteResponse
from app.services.cloudinary_service import cloudinary_service

router = APIRouter(prefix="/upload", tags=["Media Upload"])


@router.post(
    "",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload Media File",
    description="Uploads an image (JPEG, PNG, WebP) or PDF document to Cloudinary CDN via FastAPI and returns secure URL and metadata.",
)
async def upload_file(
    file: UploadFile = File(..., description="Binary file to upload"),
    folder: Optional[str] = Form("foundation-erp", description="Target folder in Cloudinary"),
    resource_type: Optional[str] = Form("auto", description="Resource type: auto, image, raw"),
) -> MediaUploadResponse:
    result = await cloudinary_service.upload_file(
        file=file,
        folder=folder,
        resource_type=resource_type or "auto",
    )
    return MediaUploadResponse(**result)


@router.post(
    "/base64",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload Base64 Media",
    description="Uploads a base64-encoded image or document to Cloudinary and returns secure URL and metadata.",
)
def upload_base64(
    payload: Base64UploadRequest,
) -> MediaUploadResponse:
    result = cloudinary_service.upload_base64(
        base64_str=payload.data,
        folder=payload.folder,
        filename=payload.filename,
    )
    return MediaUploadResponse(**result)


@router.delete(
    "/{public_id:path}",
    response_model=MediaDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Media File",
    description="Deletes a media asset from Cloudinary by its public ID.",
)
def delete_file(
    public_id: str,
    resource_type: Optional[str] = "image",
    current_user: User = Depends(require_authenticated_user),
) -> MediaDeleteResponse:
    result = cloudinary_service.delete_file(
        public_id=public_id,
        resource_type=resource_type or "image",
    )
    return MediaDeleteResponse(**result)
