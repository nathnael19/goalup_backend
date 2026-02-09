import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class Match(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tournament_id: uuid.UUID = Field(foreign_key="tournament.id")
    team_a_id: uuid.UUID = Field(foreign_key="team.id")
    team_b_id: uuid.UUID = Field(foreign_key="team.id")
    score_a: int = Field(default=0)
    score_b: int = Field(default=0)
    status: str = Field(default="scheduled") # enum: scheduled, live, finished
    start_time: datetime

    tournament: "Tournament" = Relationship(back_populates="matches")
    team_a: "Team" = Relationship(back_populates="home_matches", sa_relationship_kwargs={"foreign_keys": "Match.team_a_id"})
    team_b: "Team" = Relationship(back_populates="away_matches", sa_relationship_kwargs={"foreign_keys": "Match.team_b_id"})
