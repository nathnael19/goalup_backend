import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

class AuditLogBase(SQLModel):
    action: str = Field(max_length=255)
    entity_type: str = Field(max_length=50) # Match, Team, Player, Goal, etc.
    entity_id: str = Field(max_length=255)
    description: str = Field(max_length=500)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AuditLog(AuditLogBase, table=True):
    __tablename__ = "audit_logs"
    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )

class AuditLogRead(AuditLogBase):
    id: uuid.UUID
