from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.player import Player, PlayerCreate, PlayerRead
from app.models.team import Team

router = APIRouter()

@router.post("/", response_model=PlayerRead)
def create_player(*, session: Session = Depends(get_session), player: PlayerCreate):
    # Manual lowercase to handle any potential Enum/SQLAlchemy mismatch
    player.position = player.position.lower()
    
    # Check if jersey number is unique for the team
    existing_player = session.exec(
        select(Player).where(
            Player.team_id == player.team_id,
            Player.jersey_number == player.jersey_number
        )
    ).first()
    if existing_player:
        raise HTTPException(
            status_code=400,
            detail=f"Jersey number {player.jersey_number} is already taken in this team"
        )
    
    team = session.get(Team, player.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    db_player = Player.model_validate(player)
    session.add(db_player)
    session.commit()
    session.refresh(db_player)
    return db_player

@router.get("/", response_model=List[PlayerRead])
def read_players(session: Session = Depends(get_session)):
    players = session.exec(select(Player)).all()
    return players
