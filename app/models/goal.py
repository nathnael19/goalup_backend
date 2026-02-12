import uuid
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class GoalBase(SQLModel):
    match_id: uuid.UUID = Field(foreign_key="match.id",ondelete="CASCADE")
    player_id: Optional[uuid.UUID] = Field(default=None, foreign_key="player.id",ondelete="CASCADE")
    assistant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="player.id",ondelete="CASCADE")
    team_id: uuid.UUID = Field(foreign_key="team.id",ondelete="CASCADE")
    minute: int
    is_own_goal: bool = Field(default=False)

class Goal(GoalBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    match: "Match" = Relationship(back_populates="goals_list")
    player: Optional["Player"] = Relationship(
        back_populates="scored_goals",
        sa_relationship_kwargs={"foreign_keys": "Goal.player_id"}
    )
    assistant: Optional["Player"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Goal.assistant_id"}
    )
    team: "Team" = Relationship()

class GoalCreate(GoalBase):
    pass

class GoalRead(GoalBase):
    id: uuid.UUID

class GoalReadWithPlayer(GoalRead):
    player: Optional["PlayerRead"] = None
    assistant: Optional["PlayerRead"] = None

from app.models.match import Match
from app.models.player import Player, PlayerRead
from app.models.team import Team
