import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from supabase import create_client, Client
from app.core.config import settings

router = APIRouter()

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_PROJECT_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

@router.post("")
async def upload_file(file: UploadFile = File(...)):
    # Validate file type (simple check)
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Read file content
        content = await file.read()
        
        # Upload to Supabase Storage
        path = f"uploads/{unique_filename}"
        response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
            path=path,
            file=content,
            file_options={"content-type": file.content_type}
        )
        
        # Get public URL
        # Supabase public URL format: {URL}/storage/v1/object/public/{BUCKET}/{PATH}
        public_url = f"{settings.SUPABASE_PROJECT_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET_NAME}/{path}"
        
        return {"url": public_url}
        
    except Exception as e:
        print(f"Supabase upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload image to Supabase: {str(e)}")
    finally:
        await file.close()
