from supabase import create_client, Client
from app.core.config import settings

def get_supabase_client() -> Client:
    """Initialize and return a Supabase client."""
    return create_client(settings.SUPABASE_PROJECT_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

supabase: Client = get_supabase_client()
