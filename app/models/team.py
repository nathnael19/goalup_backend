import uuid
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class TeamBase(SQLModel):
    name: str = Field(index=True)
    batch: str
    logo_url: Optional[str] = None

class Team(TeamBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    players: List["Player"] = Relationship(back_populates="team")
    home_matches: List["Match"] = Relationship(back_populates="team_a", sa_relationship_kwargs={"foreign_keys": "Match.team_a_id"})
    away_matches: List["Match"] = Relationship(back_populates="team_b", sa_relationship_kwargs={"foreign_keys": "Match.team_b_id"})
    standings: List["Standing"] = Relationship(back_populates="team")

class TeamCreate(TeamBase):
    tournament_id: uuid.UUID

class TeamRead(TeamBase):
    id: uuid.UUID


