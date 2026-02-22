from datetime import datetime
from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel
import uuid

class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    TOURNAMENT_ADMIN = "TOURNAMENT_ADMIN"
    NEWS_REPORTER = "NEWS_REPORTER"
    COACH = "COACH"
    REFEREE = "REFEREE"

class User(SQLModel, table=True):
    """Admin user model for authentication."""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    full_name: str = Field(max_length=255)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    role: UserRole = Field(default=UserRole.REFEREE)
    
    # Association for Coaches
    team_id: Optional[uuid.UUID] = Field(default=None, foreign_key="team.id", nullable=True)
    
    # Association for Tournament Admins/Referees
    tournament_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tournament.id", nullable=True)
    
    # Association for Competition Admins
    competition_id: Optional[uuid.UUID] = Field(default=None, foreign_key="competition.id", nullable=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(SQLModel):
    email: str = Field(unique=True, index=True, max_length=255)
    full_name: str = Field(max_length=255)
    password: Optional[str] = Field(default=None, max_length=255)
    role: UserRole = Field(default=UserRole.REFEREE)
    team_id: Optional[uuid.UUID] = None
    tournament_id: Optional[uuid.UUID] = None
    competition_id: Optional[uuid.UUID] = None

class UserRead(SQLModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    role: UserRole
    team_id: Optional[uuid.UUID] = None
    tournament_id: Optional[uuid.UUID] = None
    competition_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

class UserUpdate(SQLModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    team_id: Optional[uuid.UUID] = None
    tournament_id: Optional[uuid.UUID] = None
    competition_id: Optional[uuid.UUID] = None
