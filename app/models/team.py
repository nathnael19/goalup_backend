import uuid
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class Team(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    batch: str
    logo_url: Optional[str] = None

    players: List["Player"] = Relationship(back_populates="team")
    home_matches: List["Match"] = Relationship(back_populates="team_a", sa_relationship_kwargs={"foreign_keys": "Match.team_a_id"})
    away_matches: List["Match"] = Relationship(back_populates="team_b", sa_relationship_kwargs={"foreign_keys": "Match.team_b_id"})
    standings: List["Standing"] = Relationship(back_populates="team")
