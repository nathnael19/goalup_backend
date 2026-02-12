import uuid
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime

class SubstitutionBase(SQLModel):
    match_id: uuid.UUID = Field(foreign_key="match.id",ondelete="CASCADE")
    team_id: uuid.UUID = Field(foreign_key="team.id",ondelete="CASCADE")
    player_in_id: uuid.UUID = Field(foreign_key="player.id",ondelete="CASCADE")
    player_out_id: uuid.UUID = Field(foreign_key="player.id",ondelete="CASCADE")
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

class SubstitutionReadWithPlayers(SubstitutionRead):
    player_in: Optional["PlayerRead"] = None
    player_out: Optional["PlayerRead"] = None

from app.models.match import Match
from app.models.team import Team
from app.models.player import Player, PlayerRead
