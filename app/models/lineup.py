import uuid
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class LineupBase(SQLModel):
    match_id: uuid.UUID = Field(foreign_key="match.id",ondelete="CASCADE")
    team_id: uuid.UUID = Field(foreign_key="team.id",ondelete="CASCADE")
    player_id: uuid.UUID = Field(foreign_key="player.id",ondelete="CASCADE")
    is_starting: bool = Field(default=True)
    slot_index: Optional[int] = Field(default=None)

class Lineup(LineupBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    match: "Match" = Relationship(back_populates="lineups")
    team: "Team" = Relationship()
    player: "Player" = Relationship()

class LineupRead(LineupBase):
    id: uuid.UUID

class LineupReadWithPlayer(LineupRead):
    player: Optional["PlayerRead"] = None

from app.models.match import Match
from app.models.team import Team
from app.models.player import Player, PlayerRead
