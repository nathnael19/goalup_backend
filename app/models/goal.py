import uuid
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class GoalBase(SQLModel):
    match_id: uuid.UUID = Field(foreign_key="match.id")
    player_id: Optional[uuid.UUID] = Field(default=None, foreign_key="player.id")
    team_id: uuid.UUID = Field(foreign_key="team.id")
    minute: int
    is_own_goal: bool = Field(default=False)

class Goal(GoalBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    match: "Match" = Relationship(back_populates="goals_list")
    player: Optional["Player"] = Relationship(back_populates="scored_goals")
    team: "Team" = Relationship()

class GoalCreate(GoalBase):
    pass

class GoalRead(GoalBase):
    id: uuid.UUID

from app.models.match import Match
from app.models.player import Player
from app.models.team import Team
