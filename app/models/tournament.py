import uuid
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class TournamentBase(SQLModel):
    name: str
    year: int
    type: str

class Tournament(TournamentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    matches: List["Match"] = Relationship(back_populates="tournament")
    standings: List["Standing"] = Relationship(back_populates="tournament")

class TournamentCreate(TournamentBase):
    pass

class TournamentRead(TournamentBase):
    id: uuid.UUID


