import uuid
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class Player(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    team_id: uuid.UUID = Field(foreign_key="team.id")
    goals: int = Field(default=0)
    yellow_cards: int = Field(default=0)
    red_cards: int = Field(default=0)

    team: "Team" = Relationship(back_populates="players")
