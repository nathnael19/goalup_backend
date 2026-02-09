from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.tournament import Tournament

router = APIRouter()

@router.get("/", response_model=List[Tournament])
def read_tournaments(session: Session = Depends(get_session)):
    tournaments = session.exec(select(Tournament)).all()
    return tournaments
