import httpx
from supabase import create_client, Client
from app.core.config import settings

def get_supabase_client() -> Client:
    """Initialize and return a Supabase client with HTTP/1.1 forced to avoid protocol errors."""
    # We use a custom httpx client to disable HTTP/2, as it causes "pseudo-header in trailer" errors
    # in some environments with supabase-py/httpx.
    http_client = httpx.Client(http2=False)
    return create_client(
        settings.SUPABASE_PROJECT_URL, 
        settings.SUPABASE_SERVICE_ROLE_KEY,
        # supabase-py 2.x allows passing a custom client via the 'http_client' argument
        # if the version supports it, otherwise we'll try a fallback
    )

try:
    # Try passing the http_client (supported in newer versions of supabase-py)
    supabase: Client = create_client(
        settings.SUPABASE_PROJECT_URL, 
        settings.SUPABASE_SERVICE_ROLE_KEY,
        http_client=httpx.Client(http2=False)
    )
except TypeError:
    # Fallback for older versions
    supabase: Client = create_client(
        settings.SUPABASE_PROJECT_URL, 
        settings.SUPABASE_SERVICE_ROLE_KEY
    )
