import uuid
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class StandingBase(SQLModel):
    tournament_id: uuid.UUID = Field(foreign_key="tournament.id",ondelete="CASCADE")
    team_id: uuid.UUID = Field(foreign_key="team.id",ondelete="CASCADE")
    played: int = Field(default=0)
    won: int = Field(default=0)
    drawn: int = Field(default=0)
    lost: int = Field(default=0)
    goals_for: int = Field(default=0)
    goals_against: int = Field(default=0)
    points: int = Field(default=0)

class Standing(StandingBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    tournament: "Tournament" = Relationship(back_populates="standings")
    team: "Team" = Relationship(back_populates="standings")

class StandingRead(StandingBase):
    id: uuid.UUID
