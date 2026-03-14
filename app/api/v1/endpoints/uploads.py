import logging
import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.core.supabase_client import supabase
from app.core.config import settings
from app.api.v1.deps import get_current_active_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    # Validate file type & size
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image type. Allowed: JPEG, PNG, WebP",
        )
    
    try:
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Read file content (enforce max size ~5MB)
        content = await file.read()
        max_bytes = 5 * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(status_code=400, detail="Image is too large (max 5MB)")
        
        # Upload to Supabase Storage
        path = unique_filename
        supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
            path=path,
            file=content,
            file_options={"content-type": file.content_type}
        )
        
        # Get signed URL for immediate preview (valid for 1 hour)
        # This allows the admin panel to show the image right after upload
        signed_url_response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).create_signed_url(
            path=path,
            expires_in=3600
        )
        
        # Return both the signed URL for preview and the raw path to be saved in DB
        return {
            "url": signed_url_response["signedURL"],
            "path": path
        }
        
    except Exception:
        logger.exception("Supabase upload failed")
        raise HTTPException(status_code=500, detail="Failed to upload image")
    finally:
        await file.close()
