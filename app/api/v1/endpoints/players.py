from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.player import Player

router = APIRouter()

@router.get("/", response_model=List[Player])
def read_players(session: Session = Depends(get_session)):
    players = session.exec(select(Player)).all()
    return players
