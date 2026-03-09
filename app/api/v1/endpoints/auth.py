from datetime import timedelta
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
from app.api.v1.deps import get_current_active_user
from app.core.audit import record_audit_log
from app.core.supabase import supabase

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
    OAuth2 compatible token login, authenticate with Supabase Auth.
    """
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": form_data.username,
            "password": form_data.password
        })

        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user from our public.users table to check active status and role
        user_id = auth_response.user.id
        statement = select(User).where(User.id == user_id)
        user = session.exec(statement).first()

        if not user:
            raise HTTPException(status_code=404, detail="User profile not found")

        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")

        return {
            "access_token": auth_response.session.access_token,
            "token_type": "bearer",
            "refresh_token": auth_response.session.refresh_token,
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
    for field in ["role", "is_active", "is_superuser", "current_password"]:
        if field in update_data:
            del update_data[field]

    # Handle password change via Supabase Auth Admin API
    if "password" in update_data:
        new_password = update_data.pop("password")
        try:
            supabase.auth.admin.update_user_by_id(
                str(current_user.id),
                {"password": new_password}
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update password: {str(e)}"
            )

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
def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
):
    """
    Request a password reset email via Supabase Auth.
    Supabase sends the reset email with a link pointing to ADMIN_FRONTEND_URL/reset-password.
    """
    try:
        supabase.auth.reset_password_for_email(
            data.email,
            options={
                "redirect_to": f"{settings.ADMIN_FRONTEND_URL}/reset-password"
            }
        )
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
    Set initial password using the Supabase invite token.
    The frontend exchanges the OTP token for a session and then calls this endpoint.
    """
    try:
        # Exchange the invite OTP token for a session
        session_response = supabase.auth.exchange_code_for_session({
            "auth_code": data.token
        })
        if not session_response.user:
            raise HTTPException(status_code=400, detail="Invalid or expired setup token")

        user_id = session_response.user.id
        # Update password via Admin API
        supabase.auth.admin.update_user_by_id(
            user_id,
            {"password": data.password}
        )
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
    Reset password using the Supabase reset token from the email link.
    The frontend exchanges the OTP and then calls this endpoint.
    """
    try:
        # Exchange the OTP token from the email link for a session
        session_response = supabase.auth.exchange_code_for_session({
            "auth_code": data.token
        })
        if not session_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        user_id = session_response.user.id
        # Update password via Admin API
        supabase.auth.admin.update_user_by_id(
            user_id,
            {"password": data.new_password}
        )

        # Audit log
        statement = select(User).where(User.id == user_id)
        user = session.exec(statement).first()
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
    current_user: User = Depends(get_current_active_user)
):
    """
    Log out from Supabase.
    """
    try:
        supabase.auth.sign_out()
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        # Even if Supabase signout fails (e.g. token expired), we've cleared our intent
    
    return {"message": "Successfully logged out"}
