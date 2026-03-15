from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.websockets import WebSocket, WebSocketDisconnect
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import create_db_and_tables
from app.core.security import decode_access_token
from app.core.realtime import realtime_manager, ConnectionInfo
from app.core.database import engine
from app.models.user import User
from sqlmodel import Session
import asyncio
import logging
import os
import time

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


class RealtimeBroadcastMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Fire-and-forget broadcast so response returns immediately
        if request.url.path.startswith(settings.API_V1_STR):
            if request.method in ("POST", "PUT", "PATCH", "DELETE") and 200 <= response.status_code < 300:
                rel_path = request.url.path[len(settings.API_V1_STR):].lstrip("/")
                entity = (rel_path.split("/", 1)[0] or "unknown").lower()
                action = {
                    "POST": "created",
                    "PUT": "updated",
                    "PATCH": "updated",
                    "DELETE": "deleted",
                }.get(request.method, "updated")
                payload = {
                    "type": "entity_changed",
                    "entity": entity,
                    "action": action,
                    "id": None,
                    "path": request.url.path,
                    "method": request.method,
                    "status": response.status_code,
                }

                async def _broadcast():
                    try:
                        await realtime_manager.broadcast(payload)
                    except Exception as e:
                        logger.warning("Realtime broadcast failed: %s", e)

                asyncio.create_task(_broadcast())

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


# ─── Error handling: consistent JSON and user-facing messages ─────────────────
def _validation_error_message(err: RequestValidationError) -> str:
    """Turn FastAPI/Pydantic validation errors into one readable message."""
    errors = err.errors()
    if not errors:
        return "Invalid request data."
    first = errors[0]
    loc = " ".join(str(x) for x in first.get("loc", ()) if x != "body")
    msg = first.get("msg", "Invalid value")
    if loc:
        return f"{loc}: {msg}"
    return msg


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """Ensure every HTTP error returns { \"detail\": \"single message\" }."""
    detail = exc.detail
    if isinstance(detail, list):
        detail = " ".join(str(d.get("msg", d)) for d in detail) if detail else "Error"
    return JSONResponse(status_code=exc.status_code, content={"detail": str(detail)})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return 422 with a single user-friendly validation message."""
    message = _validation_error_message(exc)
    return JSONResponse(
        status_code=422,
        content={"detail": message},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all: log and return a safe message (no internal details leaked)."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please try again later.",
        },
    )


# ─── Middleware (order matters — outermost wrapper added last) ─────────────────

# 1. Security Headers (innermost — runs on every response)
app.add_middleware(SecurityHeadersMiddleware)

# 1b. Realtime broadcast (after successful mutations)
app.add_middleware(RealtimeBroadcastMiddleware)

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
        "GoalUp! starting — env=%s | cors=%s",
        settings.ENVIRONMENT,
        settings.BACKEND_CORS_ORIGINS,
    )

# ─── Routes ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_STR)

# ─── WebSocket (Realtime) ──────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token: str | None = websocket.query_params.get("token")
    if not token:
        auth_header = websocket.headers.get("authorization") or ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()

    role = "PUBLIC"
    user_id = 0

    if token:
        payload = decode_access_token(token)
        if not payload or not payload.get("sub"):
            await websocket.close(code=1008)
            return
        try:
            user_id = int(payload["sub"])
        except Exception:
            await websocket.close(code=1008)
            return

        with Session(engine) as session:
            user = session.get(User, user_id)
            if not user or not user.is_active:
                await websocket.close(code=1008)
                return
            role = str(user.role)

    await websocket.accept()
    await realtime_manager.connect(
        websocket,
        ConnectionInfo(user_id=user_id, role=role, connected_at=time.time()),
    )

    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await realtime_manager.disconnect(websocket)

# ─── Static Files ─────────────────────────────────────────────────────────────
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
