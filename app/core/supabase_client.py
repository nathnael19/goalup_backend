import time
from supabase import create_client, Client
from app.core.config import settings

supabase: Client = create_client(settings.SUPABASE_PROJECT_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

# In-memory cache for signed URLs: { path: (signed_url, expiry_timestamp) }
_url_cache: dict[str, tuple[str, float]] = {}

# Cache TTL: 50 minutes (URLs expire in 60 min, refresh 10 min early)
_CACHE_TTL = 50 * 60


def get_signed_url(path: str, expires_in: int = 3600) -> str:
    """
    Generate a signed URL for a private storage object.
    Results are cached in memory to avoid repeated Supabase API calls.
    """
    if not path:
        return ""
    if path.startswith("http"):
        return path

    # Check cache
    now = time.time()
    cached = _url_cache.get(path)
    if cached and cached[1] > now:
        return cached[0]

    try:
        response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).create_signed_url(
            path=path,
            expires_in=expires_in
        )
        signed_url = response.get("signedURL", "")
        # Store in cache
        _url_cache[path] = (signed_url, now + _CACHE_TTL)
        return signed_url
    except Exception as e:
        print(f"Error generating signed URL for {path}: {e}")
        return ""


def get_signed_urls_batch(paths: list[str], expires_in: int = 3600) -> dict[str, str]:
    """
    Generate signed URLs for multiple paths efficiently.
    Uses cache and batches uncached paths into a single Supabase call.
    """
    result: dict[str, str] = {}
    uncached_paths: list[str] = []
    now = time.time()

    for path in paths:
        if not path:
            result[path] = ""
            continue
        if path.startswith("http"):
            result[path] = path
            continue
        cached = _url_cache.get(path)
        if cached and cached[1] > now:
            result[path] = cached[0]
        else:
            uncached_paths.append(path)

    # Fetch uncached paths individually (Supabase SDK doesn't support batch signing)
    for path in uncached_paths:
        try:
            response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).create_signed_url(
                path=path,
                expires_in=expires_in
            )
            signed_url = response.get("signedURL", "")
            _url_cache[path] = (signed_url, now + _CACHE_TTL)
            result[path] = signed_url
        except Exception as e:
            print(f"Error generating signed URL for {path}: {e}")
            result[path] = ""

    return result
