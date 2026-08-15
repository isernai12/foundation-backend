import re
import base64
import logging
from typing import Optional, Dict, Any
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "application/x-pdf",
}

# Magic numbers for binary verification
MAGIC_BYTES = {
    "jpeg": b"\xff\xd8\xff",
    "png": b"\x89PNG\r\n\x1a\n",
    "pdf": b"%PDF-",
}


def _detect_file_format(content: bytes) -> Optional[Dict[str, str]]:
    """
    Detects format from binary magic bytes.
    Returns dictionary with 'ext' (e.g. '.jpg') and 'mime' (e.g. 'image/jpeg'), or None if unsupported.
    """
    if len(content) < 4:
        return None
    # Check JPEG
    if content.startswith(MAGIC_BYTES["jpeg"]):
        return {"ext": ".jpg", "mime": "image/jpeg"}
    # Check PNG
    if content.startswith(MAGIC_BYTES["png"]):
        return {"ext": ".png", "mime": "image/png"}
    # Check PDF
    if content.startswith(MAGIC_BYTES["pdf"]):
        return {"ext": ".pdf", "mime": "application/pdf"}
    # Check WebP (RIFF....WEBP)
    if content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP":
        return {"ext": ".webp", "mime": "image/webp"}
    return None


def _is_valid_magic_bytes(content: bytes) -> bool:
    return _detect_file_format(content) is not None


class CloudinaryService:
    def __init__(self):
        self._configured = False
        self._setup_cloudinary()

    def _setup_cloudinary(self) -> None:
        """Configures Cloudinary SDK using settings."""
        if settings.CLOUDINARY_URL:
            cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL)
            self._configured = True
        elif settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True,
            )
            self._configured = True
        else:
            logger.warning("Cloudinary credentials not configured in backend settings.")

    def _ensure_configured(self) -> None:
        if not self._configured:
            self._setup_cloudinary()
        if not self._configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Media storage service is not configured on the server.",
            )

    async def upload_file(
        self,
        file: UploadFile,
        folder: Optional[str] = None,
        resource_type: str = "auto",
    ) -> Dict[str, Any]:
        """
        Validates and uploads a file to Cloudinary.
        """
        self._ensure_configured()

        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded.",
            )

        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
            )

        detected_info = _detect_file_format(content)
        if not detected_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match supported image or PDF formats.",
            )

        raw_filename = file.filename or "upload"
        
        # Check if the filename contains a genuine extension
        ext = ""
        if "." in raw_filename:
            candidate_ext = "." + raw_filename.rsplit(".", 1)[-1].lower()
            # If candidate extension is unusually long or looks like token fragments, ignore it
            if len(candidate_ext) <= 6:
                ext = candidate_ext

        # If a recognized file extension was provided, ensure it is supported
        if ext:
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                )
            sanitized_filename = raw_filename
        else:
            # When filename has no genuine extension (e.g. temporary/generated name), use the detected format extension
            ext = detected_info["ext"]
            sanitized_filename = f"{raw_filename.split('.')[0]}{ext}"

        target_folder = folder.strip("/") if folder else settings.CLOUDINARY_FOLDER

        try:
            result = cloudinary.uploader.upload(
                content,
                folder=target_folder,
                resource_type=resource_type,
                use_filename=True,
                unique_filename=True,
            )
            return {
                "success": True,
                "secure_url": result.get("secure_url"),
                "public_id": result.get("public_id"),
                "format": result.get("format") or ext.lstrip("."),
                "bytes": result.get("bytes") or file_size,
                "resource_type": result.get("resource_type"),
                "original_filename": sanitized_filename,
            }
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to upload media to Cloudinary: {str(e)}",
            )

    def upload_bytes(
        self,
        content: bytes,
        folder: Optional[str] = None,
        filename: Optional[str] = None,
        resource_type: str = "auto",
    ) -> Dict[str, Any]:
        """
        Uploads raw binary bytes to Cloudinary.
        """
        self._ensure_configured()

        file_size = len(content)
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file data.",
            )

        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
            )

        detected_info = _detect_file_format(content)
        if not detected_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match supported image or PDF formats.",
            )

        raw_filename = filename or "document"
        ext = ""
        if "." in raw_filename:
            candidate_ext = "." + raw_filename.rsplit(".", 1)[-1].lower()
            if len(candidate_ext) <= 6:
                ext = candidate_ext

        if ext:
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                )
            sanitized_filename = raw_filename
        else:
            ext = detected_info["ext"]
            sanitized_filename = f"{raw_filename.split('.')[0]}{ext}"

        target_folder = folder.strip("/") if folder else settings.CLOUDINARY_FOLDER

        try:
            result = cloudinary.uploader.upload(
                content,
                folder=target_folder,
                resource_type=resource_type,
                use_filename=True,
                unique_filename=True,
            )
            return {
                "success": True,
                "secure_url": result.get("secure_url"),
                "public_id": result.get("public_id"),
                "format": result.get("format") or ext.lstrip("."),
                "bytes": result.get("bytes") or file_size,
                "resource_type": result.get("resource_type"),
                "original_filename": sanitized_filename,
            }
        except Exception as e:
            logger.error(f"Cloudinary bytes upload failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to upload media to Cloudinary: {str(e)}",
            )

    def upload_base64(
        self,
        base64_str: str,
        folder: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Decodes base64 string (including data:image/png;base64,... headers) and uploads to Cloudinary.
        """
        clean_str = re.sub(r"^data:[^;]+;base64,", "", base64_str.strip())
        try:
            raw_bytes = base64.b64decode(clean_str)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 payload.",
            )

        return self.upload_bytes(raw_bytes, folder=folder, filename=filename)

    def delete_file(
        self,
        public_id: str,
        resource_type: str = "image",
    ) -> Dict[str, Any]:
        """
        Deletes a file from Cloudinary by public ID.
        """
        self._ensure_configured()
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
            return {
                "success": True,
                "message": "File deleted successfully",
                "result": result.get("result"),
            }
        except Exception as e:
            logger.error(f"Cloudinary deletion failed for {public_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to delete file from Cloudinary: {str(e)}",
            )


cloudinary_service = CloudinaryService()
