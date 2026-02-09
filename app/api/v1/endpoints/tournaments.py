import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.tournament import Tournament, TournamentCreate, TournamentRead, TournamentUpdate, TournamentReadWithTeams

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

@router.get("/{tournament_id}", response_model=TournamentReadWithTeams)
def read_tournament(*, session: Session = Depends(get_session), tournament_id: uuid.UUID):
    tournament = session.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournament

@router.put("/{tournament_id}", response_model=TournamentRead)
def update_tournament(
    *, session: Session = Depends(get_session), tournament_id: uuid.UUID, tournament: TournamentUpdate
):
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    tournament_data = tournament.model_dump(exclude_unset=True)
    for key, value in tournament_data.items():
        setattr(db_tournament, key, value)
    session.add(db_tournament)
    session.commit()
    session.refresh(db_tournament)
    return db_tournament

@router.delete("/{tournament_id}")
def delete_tournament(
    *, session: Session = Depends(get_session), tournament_id: uuid.UUID
):
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    session.delete(db_tournament)
    session.commit()
    return {"ok": True}
