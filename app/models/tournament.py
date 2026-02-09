import uuid
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

from app.models.standing import Standing

class TournamentBase(SQLModel):
    name: str
    year: int
    type: str

class Tournament(TournamentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    matches: List["Match"] = Relationship(back_populates="tournament")
    standings: List["Standing"] = Relationship(back_populates="tournament")
    teams: List["Team"] = Relationship(back_populates="tournaments", link_model=Standing, sa_relationship_kwargs={"overlaps": "standings,tournament,team"})

class TournamentCreate(TournamentBase):
    pass

class TournamentUpdate(SQLModel):
    name: Optional[str] = None
    year: Optional[int] = None
    type: Optional[str] = None

class TournamentRead(TournamentBase):
    id: uuid.UUID

from app.models.team import Team

class TournamentReadWithTeams(TournamentRead):
    teams: List[Team] = []


