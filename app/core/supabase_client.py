from supabase import create_client, Client
from app.core.config import settings

supabase: Client = create_client(settings.SUPABASE_PROJECT_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

def get_signed_url(path: str, expires_in: int = 3600) -> str:
    """
    Generate a signed URL for a private storage object.
    If the path is already a full URL, return it as is.
    """
    if not path:
        return ""
    if path.startswith("http"):
        return path
    
    try:
        response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).create_signed_url(
            path=path,
            expires_in=expires_in
        )
        return response.get("signedURL", "")
    except Exception as e:
        print(f"Error generating signed URL for {path}: {e}")
        return ""
