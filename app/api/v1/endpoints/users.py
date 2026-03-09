import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.user import User, UserCreate, UserRead, UserUpdate, UserRole
from app.core.config import settings
from app.api.v1.deps import get_current_superuser, get_current_management_admin
from app.core.audit import record_audit_log
from app.core.supabase import supabase

router = APIRouter()


@router.post("/", response_model=UserRead)
def create_user(
    *,
    session: Session = Depends(get_session),
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_superuser)
):
    """
    Create a new user. Only Super Admins can do this.
    Creates the Supabase Auth user first, then syncs the profile to public.users.
    """
    # Check if user already exists in our DB
    statement = select(User).where(User.email == user_in.email)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    try:
        if user_in.password:
            # Create Supabase Auth user with a known password
            auth_response = supabase.auth.admin.create_user({
                "email": user_in.email,
                "password": user_in.password,
                "email_confirm": True,
            })
        else:
            # Invite the user — Supabase sends the invite email automatically
            auth_response = supabase.auth.admin.invite_user_by_email(
                user_in.email,
                options={
                    "redirect_to": f"{settings.ADMIN_FRONTEND_URL}/setup-password",
                    "data": {"full_name": user_in.full_name, "role": user_in.role},
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create Supabase Auth user: {str(e)}"
        )

    auth_user = auth_response.user
    if not auth_user:
        raise HTTPException(status_code=500, detail="Supabase Auth did not return a user object")

    try:
        db_user = User(
            id=uuid.UUID(auth_user.id),
            email=user_in.email,
            full_name=user_in.full_name,
            role=user_in.role,
            team_id=user_in.team_id,
            tournament_id=user_in.tournament_id,
            competition_id=user_in.competition_id,
            is_active=True,
            is_superuser=(user_in.role == UserRole.SUPER_ADMIN)
        )
        session.add(db_user)

        # Audit Log
        record_audit_log(
            session,
            action="CREATE_USER",
            entity_type="User",
            entity_id=user_in.email,
            description=f"Super Admin created user {user_in.email} with role {user_in.role} (Invitation: {not user_in.password})"
        )

        session.commit()
        session.refresh(db_user)
        return db_user

    except Exception as e:
        session.rollback()
        # Clean up the Supabase Auth user since DB insert failed
        try:
            supabase.auth.admin.delete_user(auth_user.id)
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user profile in database: {str(e)}"
        )


@router.get("/", response_model=List[UserRead])
def read_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_management_admin),
    role: Optional[UserRole] = None,
    offset: int = 0,
    limit: int = 100
):
    """
    List all users. Optimized for admin use (role filtering).
    """
    statement = select(User)
    if role:
        statement = statement.where(User.role == role)

    users = session.exec(statement.offset(offset).limit(limit)).all()
    return users


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    *,
    session: Session = Depends(get_session),
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_superuser)
):
    """
    Get a specific user by ID. Only Super Admins can do this.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    *,
    session: Session = Depends(get_session),
    user_id: uuid.UUID,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_superuser)
):
    """
    Update a user. Only Super Admins can do this.
    Role/status changes are in our DB; password changes go through Supabase Auth.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_in.model_dump(exclude_unset=True)

    # Restrict personal info updates for Super Admins on the User Management page
    # They should only be allowed to update permissions/roles/status
    for field in ["full_name", "email", "current_password"]:
        if field in update_data:
            del update_data[field]

    # Handle password change via Supabase Auth Admin API
    if "password" in update_data:
        new_password = update_data.pop("password")
        try:
            supabase.auth.admin.update_user_by_id(
                str(user_id),
                {"password": new_password}
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update password in Supabase Auth: {str(e)}"
            )

    if "role" in update_data:
        db_user.is_superuser = (update_data["role"] == UserRole.SUPER_ADMIN)

    for key, value in update_data.items():
        setattr(db_user, key, value)

    session.add(db_user)

    # Audit Log
    record_audit_log(
        session,
        action="UPDATE_USER",
        entity_type="User",
        entity_id=str(user_id),
        description=f"Super Admin updated user {db_user.email}"
    )

    session.commit()
    session.refresh(db_user)
    return db_user


@router.delete("/{user_id}")
def delete_user(
    *,
    session: Session = Depends(get_session),
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_superuser)
):
    """
    Delete a user. Only Super Admins can do this.
    Removes the user from both Supabase Auth and public.users.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Super Admins cannot delete themselves")

    # Audit log before deletion
    record_audit_log(
        session,
        action="DELETE_USER",
        entity_type="User",
        entity_id=str(user_id),
        description=f"Super Admin deleted user {db_user.email}"
    )

    # Delete from our DB first
    session.delete(db_user)
    session.commit()

    # Remove from Supabase Auth (best-effort)
    try:
        supabase.auth.admin.delete_user(str(user_id))
    except Exception as e:
        # Log but don't fail — the DB record is already gone
        import logging
        logging.getLogger(__name__).warning(
            f"Failed to delete user {user_id} from Supabase Auth: {e}"
        )

    return {"ok": True}
