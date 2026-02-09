import uuid
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

from app.models.standing import Standing

class TeamBase(SQLModel):
    name: str = Field(index=True)
    batch: str
    logo_url: Optional[str] = None
    color: Optional[str] = None

class Team(TeamBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    players: List["Player"] = Relationship(back_populates="team", cascade_delete=True)
    home_matches: List["Match"] = Relationship(back_populates="team_a", sa_relationship_kwargs={"foreign_keys": "Match.team_a_id"})
    away_matches: List["Match"] = Relationship(back_populates="team_b", sa_relationship_kwargs={"foreign_keys": "Match.team_b_id"})
    standings: List["Standing"] = Relationship(back_populates="team", cascade_delete=True, sa_relationship_kwargs={"overlaps": "teams"})
    tournaments: List["Tournament"] = Relationship(back_populates="teams", link_model=Standing, sa_relationship_kwargs={"overlaps": "standings,team,tournament"})

class TeamCreate(TeamBase):
    tournament_id: uuid.UUID

class TeamUpdate(SQLModel):
    name: Optional[str] = None
    batch: Optional[str] = None
    logo_url: Optional[str] = None

class TeamRead(TeamBase):
    id: uuid.UUID

from app.models.tournament import Tournament
from app.models.player import PlayerRead
from app.models.standing import StandingRead
from app.models.match import MatchRead

class TeamReadWithTournaments(TeamRead):
    tournaments: List[Tournament] = []

class TeamRoster(SQLModel):
    goalkeepers: List[PlayerRead] = []
    defenders: List[PlayerRead] = []
    midfielders: List[PlayerRead] = []
    forwards: List[PlayerRead] = []

class TeamReadDetail(TeamRead):
    roster: TeamRoster = Field(default_factory=TeamRoster)
    standings: List[StandingRead] = []
    matches: List[MatchRead] = []


