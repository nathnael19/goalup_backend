import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class NotificationBase(SQLModel):
    title: str
    message: str
    type: str  # 'news', 'match', 'general'
    link_id: Optional[str] = None
    is_read: bool = Field(default=False)


class Notification(NotificationBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationRead(NotificationBase):
    id: uuid.UUID
    created_at: datetime


class NotificationUpdate(SQLModel):
    is_read: Optional[bool] = None
