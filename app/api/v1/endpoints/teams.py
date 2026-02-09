from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.team import Team

router = APIRouter()

@router.get("/", response_model=List[Team])
def read_teams(session: Session = Depends(get_session)):
    teams = session.exec(select(Team)).all()
    return teams
