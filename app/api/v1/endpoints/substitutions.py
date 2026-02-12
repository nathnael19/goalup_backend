import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.substitution import Substitution, SubstitutionCreate, SubstitutionRead
from app.models.match import Match
from app.models.team import Team
from app.models.player import Player
from app.api.v1.deps import get_current_active_user, get_current_referee, get_current_superuser
from app.models.user import User, UserRole
from app.core.audit import record_audit_log

router = APIRouter()

@router.post("/", response_model=SubstitutionRead)
def create_substitution(
    *, 
    session: Session = Depends(get_session), 
    substitution: SubstitutionCreate,
    current_user: User = Depends(get_current_referee)
):
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
    
    # Audit Log
    record_audit_log(
        session,
        action="ADD_SUBSTITUTION",
        entity_type="Match",
        entity_id=str(substitution.match_id),
        description=f"Recorded substitution in match {substitution.match_id}: {player_out.name} OUT, {player_in.name} IN"
    )

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
def delete_substitution(
    *, 
    session: Session = Depends(get_session), 
    substitution_id: uuid.UUID,
    current_user: User = Depends(get_current_referee)
):
    substitution = session.get(Substitution, substitution_id)
    if not substitution:
        raise HTTPException(status_code=404, detail="Substitution not found")
    # Audit Log
    record_audit_log(
        session,
        action="DELETE_SUBSTITUTION",
        entity_type="Match",
        entity_id=str(substitution.match_id),
        description=f"Deleted substitution {substitution_id} from match {substitution.match_id}"
    )

    session.delete(substitution)
    session.commit()
    return {"ok": True}
