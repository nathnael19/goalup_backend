import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.user import User, UserCreate, UserRead, UserUpdate, UserRole
from app.core.security import get_password_hash, create_access_token
from app.api.v1.deps import get_current_superuser, get_current_management_admin
from app.core.audit import record_audit_log
from app.core.email import send_invitation_email
from datetime import timedelta

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
    """
    # Check if user already exists
    statement = select(User).where(User.email == user_in.email)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    import secrets
    from app.core.security import create_access_token
    from datetime import timedelta

    # Set password or generate invitation
    password = user_in.password or secrets.token_urlsafe(16)
    
    db_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(password),
        role=user_in.role,
        team_id=user_in.team_id,
        tournament_id=user_in.tournament_id,
        competition_id=user_in.competition_id,
        is_active=True,
        is_superuser=(user_in.role == UserRole.SUPER_ADMIN)
    )
    session.add(db_user)
    session.flush() # Get the ID before commit if needed, or just commit later

    # Generate setup token if no password was provided
    if not user_in.password:
        # Token valid for 24 hours
        token = create_access_token(
            data={"sub": str(db_user.email), "type": "setup_password"},
            expires_delta=timedelta(hours=24)
        )
        # Use the new email service (runs in background)
        invitation_link = f"http://localhost:5173/setup-password?token={token}"
        background_tasks.add_task(send_invitation_email, db_user.email, invitation_link)
    
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
    user_id: int,
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
    user_id: int, 
    user_in: UserUpdate,
    current_user: User = Depends(get_current_superuser)
):
    """
    Update a user. Only Super Admins can do this.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_in.model_dump(exclude_unset=True)
    
    # Restrict personal info updates for Super Admins on the User Management page
    # They should only be allowed to update permissions/roles
    for field in ["full_name", "email", "password"]:
        if field in update_data:
            del update_data[field]
            
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
    user_id: int,
    current_user: User = Depends(get_current_superuser)
):
    """
    Delete a user. Only Super Admins can do this.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Super Admins cannot delete themselves")
        
    # Audit Log
    record_audit_log(
        session,
        action="DELETE_USER",
        entity_type="User",
        entity_id=str(user_id),
        description=f"Super Admin deleted user {db_user.email}"
    )

    session.delete(db_user)
    session.commit()
    return {"ok": True}
