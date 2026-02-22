from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import create_db_and_tables
import logging
import os

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG
)
logger = logging.getLogger(__name__)

# ─── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# ─── Security Headers Middleware ──────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Attach rate limiter state and handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── Middleware (order matters — outermost wrapper added last) ─────────────────

# 1. Security Headers (innermost — runs on every response)
app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. TrustedHost (outermost — production only)
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "goalupbackend.webcode.codes",
            "*.webcode.codes",
            "localhost",
            "127.0.0.1",
            "10.0.2.2",
        ],
    )

# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    logger.info(
        "🚀 GoalUp! starting — env=%s | cors=%s",
        settings.ENVIRONMENT,
        settings.BACKEND_CORS_ORIGINS,
    )

# ─── Routes ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_STR)

# ─── Static Files ─────────────────────────────────────────────────────────────
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
