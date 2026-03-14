import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Response
from sqlmodel import Session, select, func
from app.core.database import get_session
from app.models.user import User, UserCreate, UserRead, UserUpdate, UserRole
from app.core.config import settings
from app.api.v1.deps import get_current_superuser, get_current_management_admin, get_current_active_user
from app.core.audit import record_audit_log
from app.core.security import get_password_hash, create_password_reset_token
from app.core.email import send_invitation_email
from app.core.supabase_client import get_signed_url

logger = logging.getLogger(__name__)
router = APIRouter()

# Roles a Tournament Admin is allowed to create/manage
_TOURNAMENT_ADMIN_ALLOWED_ROLES = {UserRole.COACH, UserRole.REFEREE}


@router.post("/", response_model=UserRead)
async def create_user(
    *,
    session: Session = Depends(get_session),
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_management_admin),
):
    """
    Create a new user.
    - Super Admins can create any role.
    - Tournament Admins can only create COACH or REFEREE, scoped to their tournament.
    If a password is provided it is hashed and stored immediately.
    If no password, sends an invite email with a setup link.
    """
    # ------------------------------------------------------------------
    # RBAC guard for Tournament Admins
    # ------------------------------------------------------------------
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if user_in.role not in _TOURNAMENT_ADMIN_ALLOWED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tournament Admins can only create users with role COACH or REFEREE, not '{user_in.role}'",
            )
        # Force scope to the admin's own tournament & competition
        user_in.tournament_id = current_user.tournament_id
        user_in.competition_id = current_user.competition_id
        # Referees don't belong to a team
        if user_in.role == UserRole.REFEREE:
            user_in.team_id = None

    normalized_email = (user_in.email or "").strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Email is required")

    statement = select(User).where(User.email == normalized_email)
    if session.exec(statement).first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    hashed = get_password_hash(user_in.password) if user_in.password else ""

    db_user = User(
        email=normalized_email,
        full_name=user_in.full_name,
        hashed_password=hashed,
        role=user_in.role,
        team_id=user_in.team_id,
        tournament_id=user_in.tournament_id,
        competition_id=user_in.competition_id,
        is_active=True,
        is_superuser=(user_in.role == UserRole.SUPER_ADMIN),
        created_by_id=current_user.id,
    )

    try:
        session.add(db_user)

        record_audit_log(
            session,
            action="CREATE_USER",
            entity_type="User",
            entity_id=user_in.email,
            description=f"{current_user.role} '{current_user.email}' created user {user_in.email} with role {user_in.role}",
        )

        session.commit()
        session.refresh(db_user)
    except Exception:
        session.rollback()
        logger.exception("Failed to create user")
        raise HTTPException(status_code=500, detail="Failed to create user")

    # If no password given, email an invite link
    if not user_in.password:
        invite_token = create_password_reset_token(user_in.email, expires_hours=48)
        invite_link = f"{settings.ADMIN_FRONTEND_URL}/setup-password?token={invite_token}"
        background_tasks.add_task(send_invitation_email, user_in.email, invite_link)

    user_safe = UserRead.model_validate(db_user).model_dump()
    user_safe["profile_image_url"] = get_signed_url(db_user.profile_image_url)
    user_safe["has_password"] = bool(db_user.hashed_password)
    return user_safe


@router.get("/", response_model=List[UserRead])
def read_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_management_admin),
    role: Optional[UserRole] = None,
    offset: int = 0,
    limit: int = 100,
    response: Response = None,
):
    """
    List users.
    - Super Admins see all users.
    - Tournament Admins see only users belonging to their tournament.
    Supports role filtering via ?role= query param.
    """
    statement = select(User).where(User.is_deleted == False)  # type: ignore[comparison-overlap]

    # Scope Tournament Admins to their own tournament and only users they created
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        statement = statement.where(User.created_by_id == current_user.id)

    if role:
        statement = statement.where(User.role == role)

    total = session.exec(
        select(func.count()).select_from(statement.subquery())
    ).one()

    users = session.exec(statement.offset(offset).limit(limit)).all()
    result = []
    for u in users:
        u_dict = u.model_dump()
        u_dict["profile_image_url"] = get_signed_url(u.profile_image_url)
        u_dict["has_password"] = bool(u.hashed_password)
        result.append(u_dict)
    if response is not None:
        response.headers["X-Total-Count"] = str(total)
    return result


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    *,
    session: Session = Depends(get_session),
    user_id: int,
    current_user: User = Depends(get_current_management_admin),
):
    """Get a specific user by ID."""
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Tournament Admins can only read users within their tournament
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if db_user.tournament_id != current_user.tournament_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this user")

    user_safe = UserRead.model_validate(db_user).model_dump()
    user_safe["profile_image_url"] = get_signed_url(db_user.profile_image_url)
    user_safe["has_password"] = bool(db_user.hashed_password)
    return user_safe


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    *,
    session: Session = Depends(get_session),
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_management_admin),
):
    """
    Update a user.
    - Super Admins can update any user.
    - Tournament Admins can only update COACH/REFEREE users in their own tournament,
      and cannot escalate roles beyond those two.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # RBAC check for Tournament Admins
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if db_user.created_by_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Tournament Admins can only update users they created",
            )
        # Prevent role escalation beyond allowed roles
        if user_in.role and user_in.role not in _TOURNAMENT_ADMIN_ALLOWED_ROLES:
            raise HTTPException(
                status_code=403,
                detail=f"Tournament Admins cannot assign role '{user_in.role}'",
            )

    update_data = user_in.model_dump(exclude_unset=True)

    # Restrict personal info updates from Admin user-management page
    for field in ["full_name", "email", "current_password"]:
        update_data.pop(field, None)

    # Hash password locally
    if "password" in update_data:
        db_user.hashed_password = get_password_hash(update_data.pop("password"))

    if "role" in update_data:
        db_user.is_superuser = (update_data["role"] == UserRole.SUPER_ADMIN)

    for key, value in update_data.items():
        setattr(db_user, key, value)

    session.add(db_user)

    record_audit_log(
        session,
        action="UPDATE_USER",
        entity_type="User",
        entity_id=str(user_id),
        description=f"{current_user.role} '{current_user.email}' updated user {db_user.email}",
    )

    session.commit()
    session.refresh(db_user)
    user_safe = UserRead.model_validate(db_user).model_dump()
    user_safe["profile_image_url"] = get_signed_url(db_user.profile_image_url)
    user_safe["has_password"] = bool(db_user.hashed_password)
    return user_safe


@router.delete("/{user_id}")
def delete_user(
    *,
    session: Session = Depends(get_session),
    user_id: int,
    current_user: User = Depends(get_current_management_admin),
):
    """
    Delete (soft) a user.
    - Super Admins can delete any user.
    - Tournament Admins can only delete COACH/REFEREE users in their own tournament.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    # RBAC check for Tournament Admins
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if db_user.created_by_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Tournament Admins can only delete users they created",
            )
        if db_user.role not in _TOURNAMENT_ADMIN_ALLOWED_ROLES:
            raise HTTPException(
                status_code=403,
                detail=f"Tournament Admins cannot delete users with role '{db_user.role}'",
            )

    record_audit_log(
        session,
        action="DELETE_USER",
        entity_type="User",
        entity_id=str(user_id),
        description=f"{current_user.role} '{current_user.email}' deleted user {db_user.email}",
    )

    db_user.is_deleted = True
    db_user.is_active = False
    session.add(db_user)
    session.commit()

    return {"ok": True}


@router.post("/{user_id}/resend-setup-email")
async def resend_setup_email(
    *,
    session: Session = Depends(get_session),
    user_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_management_admin),
):
    """
    Resend the set-password invitation email to a user who hasn't set one yet.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # RBAC check for Tournament Admins
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if db_user.created_by_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Tournament Admins can only resend emails to users they created",
            )

    if db_user.hashed_password:
        raise HTTPException(
            status_code=400,
            detail="User already has a password set. They should use 'Forgot Password' instead.",
        )

    invite_token = create_password_reset_token(db_user.email, expires_hours=48)
    invite_link = f"{settings.ADMIN_FRONTEND_URL}/setup-password?token={invite_token}"
    background_tasks.add_task(send_invitation_email, db_user.email, invite_link)

    record_audit_log(
        session,
        action="RESEND_SETUP_EMAIL",
        entity_type="User",
        entity_id=db_user.email,
        description=f"{current_user.role} '{current_user.email}' resent setup email to {db_user.email}",
    )
    session.commit()

    return {"ok": True, "message": "Invitation email resent successfully"}
