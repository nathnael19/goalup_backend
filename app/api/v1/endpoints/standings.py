from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.standing import Standing

router = APIRouter()

@router.get("/", response_model=List[Standing])
def read_standings(session: Session = Depends(get_session)):
    standings = session.exec(select(Standing)).all()
    return standings
