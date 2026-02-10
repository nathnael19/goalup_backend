import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class CardType(str, Enum):
    yellow = "yellow"
    red = "red"

class CardBase(SQLModel):
    match_id: uuid.UUID = Field(foreign_key="match.id")
    player_id: uuid.UUID = Field(foreign_key="player.id")
    team_id: uuid.UUID = Field(foreign_key="team.id")
    minute: int
    type: CardType

class Card(CardBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    match: "Match" = Relationship(back_populates="cards_list")
    player: "Player" = Relationship(back_populates="cards_received")
    team: "Team" = Relationship()

class CardCreate(CardBase):
    pass

class CardRead(CardBase):
    id: uuid.UUID

class CardReadWithPlayer(CardRead):
    player: Optional["PlayerRead"] = None

from app.models.match import Match
from app.models.player import Player, PlayerRead
from app.models.team import Team
