import uuid
from enum import Enum
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime


class NewsCategory(str, Enum):
    transfer = "transfer"
    injury = "injury"
    general = "general"
    match_report = "match_report"


class NewsBase(SQLModel):
    title: str
    content: str
    category: NewsCategory = Field(default=NewsCategory.general)
    image_url: Optional[str] = None
    team_id: Optional[uuid.UUID] = Field(default=None, foreign_key="team.id",ondelete="CASCADE")
    player_id: Optional[uuid.UUID] = Field(default=None, foreign_key="player.id",ondelete="CASCADE")
    is_published: bool = Field(default=True)


class News(NewsBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    team: Optional["Team"] = Relationship()
    player: Optional["Player"] = Relationship()


class NewsCreate(NewsBase):
    pass


class NewsRead(NewsBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class NewsUpdate(SQLModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[NewsCategory] = None
    image_url: Optional[str] = None
    team_id: Optional[uuid.UUID] = None
    player_id: Optional[uuid.UUID] = None
    is_published: Optional[bool] = None


from app.models.team import Team
from app.models.player import Player
