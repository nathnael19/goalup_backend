import uuid
from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from app.core.database import get_session
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.core.supabase import supabase

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    """Get current authenticated user by verifying token with Supabase Auth."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify token with Supabase
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            raise credentials_exception
            
        user_id = uuid.UUID(user_response.user.id)
        user = session.get(User, user_id)
        if user is None:
            # If user exists in Auth but not in our table, session might be out of sync
            raise credentials_exception
    except Exception as e:
        # logger.error(f"Auth verification failed: {e}")
        raise credentials_exception
    
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure the current user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Ensure the current user is a superuser."""
    if not current_user.is_superuser and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges"
        )
    return current_user

class RoleChecker:
    """Dependency for checking if current user has one of the allowed roles."""
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The user role '{current_user.role}' is not allowed to perform this action. Required: {self.allowed_roles}"
            )
        return current_user

# Helper dependencies
get_current_coach = RoleChecker([UserRole.COACH])
get_current_referee = RoleChecker([UserRole.REFEREE])
get_current_tournament_admin = RoleChecker([UserRole.TOURNAMENT_ADMIN])
get_current_news_reporter = RoleChecker([UserRole.NEWS_REPORTER])
get_current_management_admin = RoleChecker([UserRole.SUPER_ADMIN, UserRole.TOURNAMENT_ADMIN])
get_current_match_operator = RoleChecker([UserRole.SUPER_ADMIN, UserRole.REFEREE])
