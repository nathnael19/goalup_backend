import uuid
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime

class SubstitutionBase(SQLModel):
    match_id: uuid.UUID = Field(foreign_key="match.id")
    team_id: uuid.UUID = Field(foreign_key="team.id")
    player_in_id: uuid.UUID = Field(foreign_key="player.id")
    player_out_id: uuid.UUID = Field(foreign_key="player.id")
    minute: int
    
class Substitution(SubstitutionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    match: "Match" = Relationship(back_populates="substitutions")
    team: "Team" = Relationship(back_populates="substitutions")
    player_in: "Player" = Relationship(sa_relationship_kwargs={"foreign_keys": "Substitution.player_in_id"})
    player_out: "Player" = Relationship(sa_relationship_kwargs={"foreign_keys": "Substitution.player_out_id"})

class SubstitutionCreate(SubstitutionBase):
    pass

class SubstitutionRead(SubstitutionBase):
    id: uuid.UUID
    created_at: datetime

from app.models.match import Match
from app.models.team import Team
from app.models.player import Player
