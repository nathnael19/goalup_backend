from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.match import Match

router = APIRouter()

@router.get("/", response_model=List[Match])
def read_matches(session: Session = Depends(get_session)):
    matches = session.exec(select(Match)).all()
    return matches
