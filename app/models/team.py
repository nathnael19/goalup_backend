import uuid
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

from app.models.standing import Standing

class TeamBase(SQLModel):
    name: str = Field(index=True)
    logo_url: Optional[str] = None
    color: Optional[str] = None
    stadium: Optional[str] = None

class Team(TeamBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tournament_id: uuid.UUID = Field(foreign_key="tournament.id", nullable=False,ondelete="CASCADE")

    players: List["Player"] = Relationship(back_populates="team", cascade_delete=True)
    home_matches: List["Match"] = Relationship(back_populates="team_a", sa_relationship_kwargs={"foreign_keys": "Match.team_a_id", "cascade": "all, delete-orphan"})
    away_matches: List["Match"] = Relationship(back_populates="team_b", sa_relationship_kwargs={"foreign_keys": "Match.team_b_id", "cascade": "all, delete-orphan"})
    standings: List["Standing"] = Relationship(back_populates="team", cascade_delete=True, sa_relationship_kwargs={"overlaps": "teams"})
    tournaments: List["Tournament"] = Relationship(back_populates="teams", link_model=Standing, sa_relationship_kwargs={"overlaps": "standings,team,tournament"})
    substitutions: List["Substitution"] = Relationship(back_populates="team")

class TeamCreate(TeamBase):
    tournament_id: Optional[uuid.UUID] = None

class TeamUpdate(SQLModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    tournament_id: Optional[uuid.UUID] = None
    stadium: Optional[str] = None

class TeamRead(TeamBase):
    id: uuid.UUID
    tournament_id: Optional[uuid.UUID] = None

from app.models.tournament import Tournament
from app.models.player import PlayerRead
from app.models.standing import StandingRead
from app.models.match import MatchRead
from app.models.substitution import Substitution

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


