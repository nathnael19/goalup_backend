import uuid
from sqlmodel import Field, SQLModel, Relationship

class Standing(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tournament_id: uuid.UUID = Field(foreign_key="tournament.id")
    team_id: uuid.UUID = Field(foreign_key="team.id")
    played: int = Field(default=0)
    won: int = Field(default=0)
    drawn: int = Field(default=0)
    lost: int = Field(default=0)
    goals_for: int = Field(default=0)
    goals_against: int = Field(default=0)
    points: int = Field(default=0)

    tournament: "Tournament" = Relationship(back_populates="standings")
    team: "Team" = Relationship(back_populates="standings")
