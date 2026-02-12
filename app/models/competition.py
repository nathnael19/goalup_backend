import uuid
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class CompetitionBase(SQLModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None

class Competition(CompetitionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    tournaments: List["Tournament"] = Relationship(back_populates="competition", cascade_delete=True)

class CompetitionCreate(CompetitionBase):
    pass

class CompetitionRead(CompetitionBase):
    id: uuid.UUID

class CompetitionUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

