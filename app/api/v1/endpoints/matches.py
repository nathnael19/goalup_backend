import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.match import Match, MatchCreate, MatchRead, MatchUpdate
from app.models.team import Team
from app.models.tournament import Tournament

router = APIRouter()

@router.post("/", response_model=MatchRead)
def create_match(*, session: Session = Depends(get_session), match: MatchCreate):
    # Verify tournament and teams exist
    tournament = session.get(Tournament, match.tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    team_a = session.get(Team, match.team_a_id)
    team_b = session.get(Team, match.team_b_id)
    if not team_a or not team_b:
        raise HTTPException(status_code=404, detail="One or both teams not found")
        
    db_match = Match.model_validate(match)
    session.add(db_match)
    session.commit()
    session.refresh(db_match)
    return db_match

@router.get("/", response_model=List[MatchRead])
def read_matches(
    *, session: Session = Depends(get_session), offset: int = 0, limit: int = 100
):
    matches = session.exec(select(Match).offset(offset).limit(limit)).all()
    return matches

@router.get("/{match_id}", response_model=MatchRead)
def read_match(*, session: Session = Depends(get_session), match_id: uuid.UUID):
    match = session.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match

@router.put("/{match_id}", response_model=MatchRead)
def update_match(
    *, session: Session = Depends(get_session), match_id: uuid.UUID, match: MatchUpdate
):
    db_match = session.get(Match, match_id)
    if not db_match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    match_data = match.model_dump(exclude_unset=True)
    for key, value in match_data.items():
        setattr(db_match, key, value)
        
    session.add(db_match)
    session.commit()
    session.refresh(db_match)
    return db_match

@router.delete("/{match_id}")
def delete_match(*, session: Session = Depends(get_session), match_id: uuid.UUID):
    match = session.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    session.delete(match)
    session.commit()
    return {"ok": True}
