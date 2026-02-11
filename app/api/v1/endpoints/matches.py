import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.match import Match, MatchCreate, MatchRead, MatchUpdate
from app.models.team import Team, TeamRead
from app.models.tournament import Tournament, TournamentRead

router = APIRouter()

class EnrichedMatchRead(MatchRead):
    tournament: Optional[TournamentRead] = None
    team_a: Optional[TeamRead] = None
    team_b: Optional[TeamRead] = None

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

@router.get("/", response_model=List[EnrichedMatchRead])
def read_matches(
    *, session: Session = Depends(get_session), offset: int = 0, limit: int = 100
):
    matches = session.exec(select(Match).offset(offset).limit(limit)).all()
    result = []
    for m in matches:
        em = EnrichedMatchRead.model_validate(m)
        em.tournament = session.get(Tournament, m.tournament_id)
        em.team_a = session.get(Team, m.team_a_id)
        em.team_b = session.get(Team, m.team_b_id)
        result.append(em)
    return result

@router.get("/{match_id}", response_model=EnrichedMatchRead)
def read_match(*, session: Session = Depends(get_session), match_id: uuid.UUID):
    match = session.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    em = EnrichedMatchRead.model_validate(match)
    em.tournament = session.get(Tournament, match.tournament_id)
    em.team_a = session.get(Team, match.team_a_id)
    em.team_b = session.get(Team, match.team_b_id)
    return em

@router.put("/{match_id}", response_model=MatchRead)
def update_match(
    *, session: Session = Depends(get_session), match_id: uuid.UUID, match: MatchUpdate
):
    db_match = session.get(Match, match_id)
    if not db_match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Lock match data if finished for > 1 hour
    if db_match.status == "finished" and db_match.finished_at:
        import datetime
        lock_time = db_match.finished_at + datetime.timedelta(hours=1)
        if datetime.datetime.now() > lock_time:
            raise HTTPException(
                status_code=403, 
                detail="Match data is locked and cannot be changed after 1 hour of completion"
            )

    match_data = match.model_dump(exclude_unset=True)
    
    # Auto-set finished_at when status becomes finished
    if match_data.get("status") == "finished" and db_match.status != "finished":
        import datetime
        match_data["finished_at"] = datetime.datetime.now()

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
