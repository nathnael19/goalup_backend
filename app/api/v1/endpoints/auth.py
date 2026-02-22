from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlmodel import Session, select
from app.core.config import settings
from app.core.database import get_session
from app.models.user import User, UserRead, UserUpdate
from app.api.v1.deps import get_current_active_user
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.audit import record_audit_log

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session)
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    # Find user by email (username field in OAuth2 form)
    statement = select(User).where(User.email == form_data.username)
    user = session.exec(statement).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

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
    # These should be managed by Super Admins via /users/{user_id}
    if "role" in update_data:
        del update_data["role"]
    if "is_active" in update_data:
        del update_data["is_active"]
    if "is_superuser" in update_data:
        del update_data["is_superuser"]

    if "password" in update_data:
        # Check current password if provided
        if not update_data.get("current_password"):
            raise HTTPException(status_code=400, detail="Current password is required to change password")
        
        if not verify_password(update_data.pop("current_password"), current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect current password")
            
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    elif "current_password" in update_data:
        del update_data["current_password"]

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

from pydantic import BaseModel
class SetupPasswordRequest(BaseModel):
    token: str
    password: str

@router.post("/setup-password")
def setup_password(
    data: SetupPasswordRequest,
    session: Session = Depends(get_session)
):
    """
    Set user password using a setup token.
    """
    from app.core.security import decode_access_token, get_password_hash
    
    payload = decode_access_token(data.token)
    if not payload or payload.get("type") != "setup_password":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired setup token"
        )
    
    email = payload.get("sub")
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.hashed_password = get_password_hash(data.password)
    session.add(user)
    session.commit()
    
    return {"message": "Password set successfully"}
