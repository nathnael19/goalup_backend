import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class MatchStatus(str, Enum):
    scheduled = "scheduled"
    live = "live"
    finished = "finished"

class MatchBase(SQLModel):
    tournament_id: uuid.UUID = Field(foreign_key="tournament.id",ondelete="CASCADE")
    team_a_id: uuid.UUID = Field(foreign_key="team.id",ondelete="CASCADE")
    team_b_id: uuid.UUID = Field(foreign_key="team.id",ondelete="CASCADE")
    score_a: int = Field(default=0)
    score_b: int = Field(default=0)
    status: MatchStatus = Field(default=MatchStatus.scheduled)
    start_time: datetime
    additional_time_first_half: int = Field(default=0)
    additional_time_second_half: int = Field(default=0)
    total_time: int = Field(default=90)
    is_halftime: bool = Field(default=False)
    first_half_start: Optional[datetime] = None
    second_half_start: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    match_day: int = Field(default=1, index=True)
    stage: Optional[str] = Field(default=None, index=True) # e.g. "Round of 16", "Quarter-final"
    penalty_score_a: int = Field(default=0)
    penalty_score_b: int = Field(default=0)
    is_extra_time: bool = Field(default=False)
    formation_a: str = Field(default="4-3-3")
    formation_b: str = Field(default="4-3-3")

class Match(MatchBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    tournament: "Tournament" = Relationship(back_populates="matches")
    team_a: "Team" = Relationship(back_populates="home_matches", sa_relationship_kwargs={"foreign_keys": "Match.team_a_id"})
    team_b: "Team" = Relationship(back_populates="away_matches", sa_relationship_kwargs={"foreign_keys": "Match.team_b_id"})
    goals_list: List["Goal"] = Relationship(back_populates="match", cascade_delete=True)
    cards_list: List["Card"] = Relationship(back_populates="match", cascade_delete=True)
    substitutions: List["Substitution"] = Relationship(back_populates="match", cascade_delete=True)
    lineups: List["Lineup"] = Relationship(back_populates="match", cascade_delete=True)

class MatchCreate(MatchBase):
    pass

class MatchRead(MatchBase):
    id: uuid.UUID

class MatchUpdate(SQLModel):
    tournament_id: Optional[uuid.UUID] = None
    team_a_id: Optional[uuid.UUID] = None
    team_b_id: Optional[uuid.UUID] = None
    score_a: Optional[int] = None
    score_b: Optional[int] = None
    status: Optional[MatchStatus] = None
    start_time: Optional[datetime] = None
    additional_time_first_half: Optional[int] = None
    additional_time_second_half: Optional[int] = None
    total_time: Optional[int] = None
    is_halftime: Optional[bool] = None
    first_half_start: Optional[datetime] = None
    second_half_start: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    match_day: Optional[int] = None
    formation_a: Optional[str] = None
    formation_b: Optional[str] = None

from app.models.card import Card
from app.models.goal import Goal
from app.models.tournament import Tournament
from app.models.team import Team
from app.models.substitution import Substitution
from app.models.lineup import Lineup
