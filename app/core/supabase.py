# This file previously provided a Supabase Auth client.
# Auth is now handled with custom JWT (see app/core/security.py).
# The Supabase client here is kept ONLY for storage operations compatibility
# if anything imports from this module directly.
#
# For storage operations, use app/core/supabase_client.py instead.

from app.core.supabase_client import supabase  # re-export for backwards-compat
