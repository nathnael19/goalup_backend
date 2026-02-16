import uuid
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

from app.models.standing import Standing

class TournamentBase(SQLModel):
    name: str
    year: int
    type: str = Field(default="league") # "league", "knockout", "group_knockout"
    competition_id: Optional[uuid.UUID] = Field(default=None, foreign_key="competition.id")
    knockout_legs: int = Field(default=1) # 1 or 2
    has_third_place_match: bool = Field(default=False)

class Tournament(TournamentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    competition: Optional["Competition"] = Relationship(back_populates="tournaments")
    matches: List["Match"] = Relationship(back_populates="tournament", cascade_delete=True)
    standings: List["Standing"] = Relationship(back_populates="tournament", cascade_delete=True)
    teams: List["Team"] = Relationship(back_populates="tournaments", link_model=Standing, sa_relationship_kwargs={"overlaps": "standings,tournament,team"})
    
    # Direct relationship to handle cascade delete of teams belonging to this tournament
    registered_teams: List["Team"] = Relationship(sa_relationship_kwargs={"cascade": "all, delete-orphan", "foreign_keys": "Team.tournament_id"})

class TournamentCreate(TournamentBase):
    pass

class TournamentScheduleCreate(SQLModel):
    start_date: datetime
    interval_days: int = Field(default=1)
    matches_per_day: int = Field(default=1)
    total_time: int = Field(default=90)

class TournamentKnockoutCreate(TournamentScheduleCreate):
    stage_interval_days: int = Field(default=7) # Days between rounds
    generate_third_place: bool = Field(default=False)

class TournamentUpdate(SQLModel):
    name: Optional[str] = None
    year: Optional[int] = None
    type: Optional[str] = None

class TournamentRead(TournamentBase):
    id: uuid.UUID

from app.models.team import Team

class TournamentReadWithTeams(TournamentRead):
    teams: List[Team] = []


