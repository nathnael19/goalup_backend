from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.tournament import Tournament, TournamentCreate, TournamentRead

router = APIRouter()

@router.post("/", response_model=TournamentRead)
def create_tournament(*, session: Session = Depends(get_session), tournament: TournamentCreate):
    db_tournament = Tournament.model_validate(tournament)
    session.add(db_tournament)
    session.commit()
    session.refresh(db_tournament)
    return db_tournament

@router.get("/", response_model=List[TournamentRead])
def read_tournaments(session: Session = Depends(get_session)):
    tournaments = session.exec(select(Tournament)).all()
    return tournaments
