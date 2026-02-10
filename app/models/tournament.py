import uuid
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

from app.models.standing import Standing

class TournamentBase(SQLModel):
    name: str
    year: int
    type: str
    image_url: Optional[str] = None

class Tournament(TournamentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    matches: List["Match"] = Relationship(back_populates="tournament", cascade_delete=True)
    standings: List["Standing"] = Relationship(back_populates="tournament", cascade_delete=True)
    teams: List["Team"] = Relationship(back_populates="tournaments", link_model=Standing, sa_relationship_kwargs={"overlaps": "standings,tournament,team"})

class TournamentCreate(TournamentBase):
    pass

class TournamentScheduleCreate(SQLModel):
    start_date: datetime
    interval_days: int = Field(default=1)
    matches_per_day: int = Field(default=1)
    total_time: int = Field(default=90)

class TournamentUpdate(SQLModel):
    name: Optional[str] = None
    year: Optional[int] = None
    type: Optional[str] = None
    image_url: Optional[str] = None

class TournamentRead(TournamentBase):
    id: uuid.UUID

from app.models.team import Team

class TournamentReadWithTeams(TournamentRead):
    teams: List[Team] = []


