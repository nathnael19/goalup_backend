import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.competition import Competition, CompetitionCreate, CompetitionRead, CompetitionUpdate
from app.core.supabase_client import get_signed_url
from app.api.v1.deps import get_current_management_admin, get_current_active_user
from app.models.user import User, UserRole
from app.models.team import Team
from app.models.tournament import Tournament
from app.models.match import Match

router = APIRouter()

@router.post("/", response_model=CompetitionRead)
def create_competition(
    *, 
    session: Session = Depends(get_session), 
    competition: CompetitionCreate,
    current_user: User = Depends(get_current_management_admin)
):
    db_competition = Competition.model_validate(competition)
    session.add(db_competition)
    session.commit()
    session.refresh(db_competition)
    
    res = db_competition.model_dump()
    res["image_url"] = get_signed_url(db_competition.image_url)
    return res

@router.get("/", response_model=List[CompetitionRead])
def read_competitions(
    *, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role == UserRole.TOURNAMENT_ADMIN and current_user.competition_id:
        competitions = session.exec(select(Competition).where(Competition.id == current_user.competition_id)).all()
    elif current_user.role == UserRole.REFEREE:
        # Resolve competition through tournament_id or assigned matches
        tournament_ids = set()
        if current_user.tournament_id:
            tournament_ids.add(current_user.tournament_id)
        
        # Also find tournaments from matches where they are the referee
        match_tournament_ids = session.exec(
            select(Match.tournament_id).where(Match.referee_id == current_user.id)
        ).all()
        for t_id in match_tournament_ids:
            tournament_ids.add(t_id)
            
        if tournament_ids:
            # Get competition IDs from these tournaments
            comp_ids = session.exec(
                select(Tournament.competition_id)
                .where(Tournament.id.in_(list(tournament_ids)))
            ).all()
            
            if comp_ids:
                competitions = session.exec(
                    select(Competition).where(Competition.id.in_(list(set(comp_ids))))
                ).all()
            else:
                competitions = []
        else:
            competitions = []
    elif current_user.role == UserRole.COACH:
        # Resolve competition through team → tournament → competition
        if current_user.team_id:
            team = session.get(Team, current_user.team_id)
            if team and team.tournament_id:
                tournament = session.get(Tournament, team.tournament_id)
                if tournament and tournament.competition_id:
                    competitions = session.exec(
                        select(Competition).where(Competition.id == tournament.competition_id)
                    ).all()
                else:
                    competitions = []
            else:
                competitions = []
        else:
            competitions = []
    elif current_user.role in (UserRole.SUPER_ADMIN, UserRole.TOURNAMENT_ADMIN):
        competitions = session.exec(select(Competition)).all()
    else:
        raise HTTPException(status_code=403, detail="Not authorised to view competitions")
        
    results = []
    for c in competitions:
        c_dict = c.model_dump()
        c_dict["image_url"] = get_signed_url(c.image_url)
        results.append(c_dict)
    return results

@router.get("/{competition_id}", response_model=CompetitionRead)
def read_competition(
    *, 
    session: Session = Depends(get_session), 
    competition_id: uuid.UUID,
    current_user: User = Depends(get_current_management_admin)
):
    if current_user.role == UserRole.TOURNAMENT_ADMIN and current_user.competition_id != competition_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this competition")
        
    competition = session.get(Competition, competition_id)
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    
    res = competition.model_dump()
    res["image_url"] = get_signed_url(competition.image_url)
    return res

@router.put("/{competition_id}", response_model=CompetitionRead)
def update_competition(
    *, 
    session: Session = Depends(get_session), 
    competition_id: uuid.UUID, 
    competition: CompetitionUpdate,
    current_user: User = Depends(get_current_management_admin)
):
    if current_user.role == UserRole.TOURNAMENT_ADMIN and current_user.competition_id != competition_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this competition")
        
    db_competition = session.get(Competition, competition_id)
    if not db_competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    competition_data = competition.model_dump(exclude_unset=True)
    for key, value in competition_data.items():
        setattr(db_competition, key, value)
    session.add(db_competition)
    session.commit()
    session.refresh(db_competition)
    
    res = db_competition.model_dump()
    res["image_url"] = get_signed_url(db_competition.image_url)
    return res

@router.delete("/{competition_id}")
def delete_competition(
    *, 
    session: Session = Depends(get_session), 
    competition_id: uuid.UUID,
    current_user: User = Depends(get_current_management_admin)
):
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
         raise HTTPException(status_code=403, detail="Tournament Admins cannot delete competitions")
         
    competition = session.get(Competition, competition_id)
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    session.delete(competition)
    session.commit()
    return {"ok": True}
