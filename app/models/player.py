from enum import Enum
import uuid
from typing import Optional
from pydantic import field_validator
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel, Relationship

class Position(str, Enum):
    cb = "cb"
    cdm = "cdm"
    cam = "cam"
    cm = "cm"
    st = "st"
    lw = "lw"
    rw = "rw"
    rb = "rb"
    lb = "lb"
    gk = "gk" 

class PlayerBase(SQLModel):
    name: str
    team_id: uuid.UUID = Field(foreign_key="team.id")
    jersey_number: int
    position: Position
    goals: int = Field(default=0)
    yellow_cards: int = Field(default=0)
    red_cards: int = Field(default=0)

    @field_validator("position", mode="before")
    @classmethod
    def lowercase_position(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.lower()
            return v
        if isinstance(v, Position):
            return v.value.lower()
        return v

class Player(PlayerBase, table=True):
    __table_args__ = (
        UniqueConstraint("team_id", "jersey_number", name="unique_team_jersey"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    team: "Team" = Relationship(back_populates="players")

class PlayerCreate(PlayerBase):
    pass

class PlayerRead(PlayerBase):
    id: uuid.UUID
