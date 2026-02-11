import uuid
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class LineupBase(SQLModel):
    match_id: uuid.UUID = Field(foreign_key="match.id")
    team_id: uuid.UUID = Field(foreign_key="team.id")
    player_id: uuid.UUID = Field(foreign_key="player.id")
    is_starting: bool = Field(default=True)

class Lineup(LineupBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    match: "Match" = Relationship(back_populates="lineups")
    team: "Team" = Relationship()
    player: "Player" = Relationship()

class LineupRead(LineupBase):
    id: uuid.UUID

from app.models.match import Match
from app.models.team import Team
from app.models.player import Player
