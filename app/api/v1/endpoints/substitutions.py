import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.substitution import Substitution, SubstitutionCreate, SubstitutionRead
from app.models.match import Match
from app.models.team import Team
from app.models.player import Player

router = APIRouter()

@router.post("/", response_model=SubstitutionRead)
def create_substitution(*, session: Session = Depends(get_session), substitution: SubstitutionCreate):
    match = session.get(Match, substitution.match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
        
    team = session.get(Team, substitution.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    player_in = session.get(Player, substitution.player_in_id)
    if not player_in:
        raise HTTPException(status_code=404, detail="Player In not found")

    player_out = session.get(Player, substitution.player_out_id)
    if not player_out:
        raise HTTPException(status_code=404, detail="Player Out not found")
        
    db_substitution = Substitution.model_validate(substitution)
    session.add(db_substitution)
    session.commit()
    session.refresh(db_substitution)
    return db_substitution

@router.get("/match/{match_id}", response_model=List[SubstitutionRead])
def read_substitutions_by_match(
    *, session: Session = Depends(get_session), match_id: uuid.UUID
):
    substitutions = session.exec(select(Substitution).where(Substitution.match_id == match_id)).all()
    return substitutions

@router.delete("/{substitution_id}")
def delete_substitution(*, session: Session = Depends(get_session), substitution_id: uuid.UUID):
    substitution = session.get(Substitution, substitution_id)
    if not substitution:
        raise HTTPException(status_code=404, detail="Substitution not found")
    session.delete(substitution)
    session.commit()
    return {"ok": True}
