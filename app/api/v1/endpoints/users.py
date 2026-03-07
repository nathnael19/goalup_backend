from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Response
from sqlmodel import Session, select, func
from app.core.database import get_session
from app.models.user import User, UserCreate, UserRead, UserUpdate, UserRole
from app.core.config import settings
from app.api.v1.deps import get_current_superuser, get_current_management_admin
from app.core.audit import record_audit_log
from app.core.security import get_password_hash, create_password_reset_token
from app.core.email import send_invitation_email
from app.core.supabase_client import get_signed_url

router = APIRouter()


@router.post("/", response_model=UserRead)
async def create_user(
    *,
    session: Session = Depends(get_session),
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_superuser),
):
    """
    Create a new user. Only Super Admins can do this.
    If a password is provided it is hashed and stored immediately.
    If no password, sends an invite email with a setup link.
    """
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
    )

    try:
        session.add(db_user)

        record_audit_log(
            session,
            action="CREATE_USER",
            entity_type="User",
            entity_id=user_in.email,
            description=f"Super Admin created user {user_in.email} with role {user_in.role}",
        )

        session.commit()
        session.refresh(db_user)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

    # If no password given, email an invite link
    if not user_in.password:
        invite_token = create_password_reset_token(user_in.email, expires_hours=48)
        invite_link = f"{settings.ADMIN_FRONTEND_URL}/setup-password?token={invite_token}"
        background_tasks.add_task(send_invitation_email, user_in.email, invite_link)

    user_dict = db_user.model_dump()
    user_dict["profile_image_url"] = get_signed_url(db_user.profile_image_url)
    return user_dict


@router.get("/", response_model=List[UserRead])
def read_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_management_admin),
    role: Optional[UserRole] = None,
    offset: int = 0,
    limit: int = 100,
    response: Response = None,
):
    """List all users. Supports role filtering."""
    statement = select(User).where(User.is_deleted == False)  # type: ignore[comparison-overlap]
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
        result.append(u_dict)
    if response is not None:
        response.headers["X-Total-Count"] = str(total)
    return result


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    *,
    session: Session = Depends(get_session),
    user_id: int,
    current_user: User = Depends(get_current_superuser),
):
    """Get a specific user by ID. Only Super Admins."""
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    user_dict = db_user.model_dump()
    user_dict["profile_image_url"] = get_signed_url(db_user.profile_image_url)
    return user_dict


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    *,
    session: Session = Depends(get_session),
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_superuser),
):
    """
    Update a user. Only Super Admins.
    Role/status changes are in our DB; password changes are hashed locally.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

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
        description=f"Super Admin updated user {db_user.email}",
    )

    session.commit()
    session.refresh(db_user)
    user_dict = db_user.model_dump()
    user_dict["profile_image_url"] = get_signed_url(db_user.profile_image_url)
    return user_dict


@router.delete("/{user_id}")
def delete_user(
    *,
    session: Session = Depends(get_session),
    user_id: int,
    current_user: User = Depends(get_current_superuser),
):
    """Delete a user. Only Super Admins. Removes from DB only."""
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Super Admins cannot delete themselves")

    record_audit_log(
        session,
        action="DELETE_USER",
        entity_type="User",
        entity_id=str(user_id),
        description=f"Super Admin deleted user {db_user.email}",
    )

    db_user.is_deleted = True
    db_user.is_active = False
    session.add(db_user)
    session.commit()

    return {"ok": True}
