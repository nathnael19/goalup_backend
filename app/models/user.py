from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
from enum import Enum
from sqlmodel import Field, SQLModel
from pydantic import field_validator

class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    TOURNAMENT_ADMIN = "TOURNAMENT_ADMIN"
    NEWS_REPORTER = "NEWS_REPORTER"
    COACH = "COACH"
    REFEREE = "REFEREE"
    VIEWER = "VIEWER"

class User(SQLModel, table=True):
    """Admin user profile — credentials managed locally."""
    __tablename__ = "users"

    # Neon schema uses SERIAL/INTEGER PK
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    full_name: str = Field(max_length=255)
    # DB column is NOT NULL; empty string means "password not set yet"
    hashed_password: str = Field(default="", max_length=255)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    role: UserRole = Field(default=UserRole.REFEREE)
    profile_image_url: Optional[str] = Field(default=None, max_length=512)
    
    # Association for Coaches
    team_id: Optional[uuid.UUID] = Field(default=None, foreign_key="team.id", nullable=True)
    
    # Association for Tournament Admins/Referees
    tournament_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tournament.id", nullable=True)
    
    competition_id: Optional[uuid.UUID] = Field(default=None, foreign_key="competition.id", nullable=True)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Account lockout / soft delete
    failed_login_attempts: int = Field(default=0)
    lockout_until: Optional[datetime] = Field(default=None, nullable=True)
    is_deleted: bool = Field(default=False)
    
    # Ownership tracking
    created_by_id: Optional[int] = Field(default=None, nullable=True)

class UserCreate(SQLModel):
    email: str = Field(unique=True, index=True, max_length=255)
    full_name: str = Field(max_length=255)
    password: Optional[str] = Field(default=None, max_length=255)
    role: UserRole = Field(default=UserRole.REFEREE)
    team_id: Optional[uuid.UUID] = None
    tournament_id: Optional[uuid.UUID] = None
    competition_id: Optional[uuid.UUID] = None

    @field_validator("team_id", "tournament_id", "competition_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

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
    profile_image_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None

class UserUpdate(SQLModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    current_password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    team_id: Optional[uuid.UUID] = None
    tournament_id: Optional[uuid.UUID] = None
    competition_id: Optional[uuid.UUID] = None
    profile_image_url: Optional[str] = None

    @field_validator("team_id", "tournament_id", "competition_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v
