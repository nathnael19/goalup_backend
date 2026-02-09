import uuid
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class Tournament(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    year: int
    type: str

    matches: List["Match"] = Relationship(back_populates="tournament")
    standings: List["Standing"] = Relationship(back_populates="tournament")
