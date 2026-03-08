import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlmodel import Session, select
from app.core.config import settings
from app.core.database import get_session
from app.models.user import User, UserRead, UserUpdate
from app.api.v1.deps import get_current_active_user, get_current_user_optional
from app.core.audit import record_audit_log
from app.core.email import send_reset_password_email
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    create_password_reset_token,
    verify_password_reset_token,
)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session)
):
    """
    OAuth2 compatible token login using local DB credentials.
    """
    try:
        email = (form_data.username or "").strip().lower()
        password = form_data.password or ""
        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")

        if not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password not set. Please use your invitation link to set a password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token(str(user.id))
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
            "user": user
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
def refresh_token(
    data: RefreshTokenRequest,
    db_session: Session = Depends(get_session)
):
    """
    Exchange a refresh token for a new access token. No auth required.
    """
    try:
        payload = decode_refresh_token(data.refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            user_int_id = int(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = db_session.get(User, user_int_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        access_token = create_access_token({"sub": str(user.id)})
        # rotate refresh token to reduce replay risk
        refresh_token_new = create_refresh_token(str(user.id))
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token_new,
            "user": user
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserRead)
def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user.
    """
    return current_user


@router.patch("/me", response_model=UserRead)
def update_user_me(
    *,
    session: Session = Depends(get_session),
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update current user's profile.
    """
    update_data = user_in.model_dump(exclude_unset=True)

    # Do not allow users to change their own role or active status via this endpoint
    for field in ["role", "is_active", "is_superuser"]:
        if field in update_data:
            del update_data[field]

    # Handle password change locally (require current password if already set)
    if "password" in update_data:
        new_password = str(update_data.pop("password") or "")
        current_password = user_in.current_password
        if current_user.hashed_password:
            if not current_password or not verify_password(current_password, current_user.hashed_password):
                raise HTTPException(status_code=400, detail="Current password is incorrect")
        if len(new_password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
        current_user.hashed_password = get_password_hash(new_password)

    for key, value in update_data.items():
        setattr(current_user, key, value)

    session.add(current_user)

    # Audit Log
    record_audit_log(
        session,
        action="UPDATE_SELF_PROFILE",
        entity_type="User",
        entity_id=str(current_user.id),
        description=f"User {current_user.email} updated their own profile"
    )

    session.commit()
    session.refresh(current_user)
    return current_user


class ForgotPasswordRequest(BaseModel):
    email: str


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """
    Request a password reset email.
    Always returns success to prevent account enumeration.
    """
    try:
        email = (data.email or "").strip().lower()
        if email:
            user = session.exec(select(User).where(User.email == email)).first()
            if user and user.is_active:
                reset_token = create_password_reset_token(email, expires_hours=2)
                reset_link = f"{settings.ADMIN_FRONTEND_URL}/reset-password?token={reset_token}"
                background_tasks.add_task(send_reset_password_email, email, reset_link)
    except Exception as e:
        # Log but always return success to prevent account enumeration
        logger.warning(f"Password reset request failed for {data.email}: {e}")

    return {"message": "If an account with this email exists, instructions have been sent."}


class SetupPasswordRequest(BaseModel):
    token: str
    password: str


@router.post("/setup-password")
def setup_password(
    data: SetupPasswordRequest,
    session: Session = Depends(get_session)
):
    """
    Set initial password using our invitation token (JWT from `create_password_reset_token`).
    """
    try:
        email = verify_password_reset_token(data.token)
        if not email:
            raise HTTPException(status_code=400, detail="Invalid or expired setup token")
        user = session.exec(select(User).where(User.email == email)).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=400, detail="Invalid or expired setup token")

        if user.hashed_password:
            raise HTTPException(status_code=400, detail="Password is already set. Please log in.")
        if len(data.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

        user.hashed_password = get_password_hash(data.password)
        session.add(user)
        session.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Setup password failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired setup token"
        )

    return {"message": "Password set successfully"}


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/reset-password")
@limiter.limit("3/minute")
def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    session: Session = Depends(get_session)
):
    """
    Reset password using our reset token (JWT from `create_password_reset_token`).
    """
    try:
        email = verify_password_reset_token(data.token)
        if not email:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        user = session.exec(select(User).where(User.email == email)).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        if len(data.new_password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

        user.hashed_password = get_password_hash(data.new_password)
        session.add(user)
        session.commit()

        # Audit log
        if user:
            record_audit_log(
                session,
                action="RESET_PASSWORD",
                entity_type="User",
                entity_id=str(user.id),
                description=f"User {user.email} reset their password"
            )
            session.commit()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    return {"message": "Password reset successfully"}


@router.post("/logout")
def logout(
    current_user: User | None = Depends(get_current_user_optional)
):
    """
    Stateless logout for JWT. Auth is optional so expired tokens can still "logout" (frontend clears state).
    """
    return {"message": "Successfully logged out"}
