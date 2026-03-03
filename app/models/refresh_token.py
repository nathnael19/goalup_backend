from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlmodel import Field, SQLModel


class RefreshToken(SQLModel, table=True):
    """Persisted refresh token for revocation / rotation tracking."""

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    jti: str = Field(index=True, unique=True, max_length=64)
    user_id: int = Field(index=True)
    revoked: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    revoked_at: Optional[datetime] = Field(default=None, nullable=True)
    expires_at: datetime

