import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from app.core.database import get_session
from app.models.team import Team, TeamCreate, TeamRead, TeamUpdate, TeamReadWithTournaments, TeamReadDetail
from app.models.standing import Standing
from app.models.tournament import Tournament, TournamentRead
from app.api.v1.deps import get_current_tournament_admin, get_current_superuser, get_current_active_user
from app.models.user import User, UserRole
from app.core.audit import record_audit_log
from app.core.supabase_client import get_signed_url, get_signed_urls_batch

router = APIRouter()

@router.post("/", response_model=TeamRead)
def create_team(
    *, 
    session: Session = Depends(get_session), 
    team: TeamCreate,
    current_user: User = Depends(get_current_tournament_admin)
):
    # RBAC Check: Tournament Admins can only create teams for THEIR tournament
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if current_user.tournament_id != team.tournament_id:
            raise HTTPException(status_code=403, detail="Tournament Admins can only create teams for their assigned tournament")

    # Verify tournament exists
    tournament = session.get(Tournament, team.tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    # Tournament ID is now part of the model, so we can validate directly
    db_team = Team.model_validate(team)
    session.add(db_team)
    
    # Audit Log
    record_audit_log(
        session,
        action="CREATE",
        entity_type="Team",
        entity_id=str(db_team.id),
        description=f"Created team: {db_team.name}"
    )

    session.commit()
    session.commit()
    session.refresh(db_team)

    # Create initial standing for the team in the tournament (still needed for stats)
    standing = Standing(tournament_id=team.tournament_id, team_id=db_team.id)
    session.add(standing)
    session.commit()

    res = db_team.model_dump()
    res["logo_url"] = get_signed_url(db_team.logo_url)
    return res

    
class TeamReadWithTournament(TeamRead):
    tournament: Optional[TournamentRead] = None
    
@router.get("/", response_model=List[TeamReadWithTournament])
def read_teams(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    query = select(Team)
    
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if current_user.tournament_id:
            query = query.where(Team.tournament_id == current_user.tournament_id)
        elif current_user.competition_id:
            query = query.join(Tournament).where(Tournament.competition_id == current_user.competition_id)
            
    teams = session.exec(query).all()
    
    # Pre-load all needed tournaments in one query
    tournament_ids = {t.tournament_id for t in teams if t.tournament_id}
    tournaments_map = {}
    if tournament_ids:
        tournaments = session.exec(select(Tournament).where(Tournament.id.in_(tournament_ids))).all()
        tournaments_map = {t.id: t for t in tournaments}
    
    # Batch sign all logo URLs
    logo_paths = [t.logo_url for t in teams if t.logo_url]
    signed_urls = get_signed_urls_batch(logo_paths) if logo_paths else {}
    
    result = []
    for t in teams:
        tt = TeamReadWithTournament.model_validate(t)
        if t.tournament_id and t.tournament_id in tournaments_map:
            tt.tournament = tournaments_map[t.tournament_id]
        
        tt_dict = tt.model_dump()
        tt_dict["logo_url"] = signed_urls.get(t.logo_url, "") if t.logo_url else ""
        result.append(tt_dict)
    return result


@router.get("/{team_id}", response_model=TeamReadDetail)
def read_team(
    *, 
    session: Session = Depends(get_session), 
    team_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user)
):
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # RBAC Check
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if current_user.tournament_id and team.tournament_id != current_user.tournament_id:
             raise HTTPException(status_code=403, detail="Not authorized to access this team")
        if current_user.competition_id:
            # Check if team's tournament belongs to the competition
            tournament = session.get(Tournament, team.tournament_id)
            if tournament and tournament.competition_id != current_user.competition_id:
                raise HTTPException(status_code=403, detail="Not authorized to access this team")
    
    # Combine home and away matches
    all_matches = team.home_matches + team.away_matches
    # Sort by start_time descending
    all_matches.sort(key=lambda x: x.start_time, reverse=True)
    
    # Categorize players into roster
    roster_data = {
        "goalkeepers": [],
        "defenders": [],
        "midfielders": [],
        "forwards": []
    }
    
    for p in team.players:
        pos = p.position.lower()
        if pos == "gk":
            roster_data["goalkeepers"].append(p)
        elif pos in ["cb", "rb", "lb"]:
            roster_data["defenders"].append(p)
        elif pos in ["cdm", "cam", "cm"]:
            roster_data["midfielders"].append(p)
        elif pos in ["st", "lw", "rw"]:
            roster_data["forwards"].append(p)
    
    # Create the detailed response
    response_data = team.model_dump()
    response_data["roster"] = roster_data
    response_data["standings"] = team.standings
    response_data["matches"] = all_matches
    
    # Sign logo
    response_data["logo_url"] = get_signed_url(team.logo_url)
    
    # Sign player photos in roster
    for category in roster_data:
        signed_players = []
        for p in roster_data[category]:
             p_dict = p.model_dump()
             p_dict["image_url"] = get_signed_url(p.image_url)
             signed_players.append(p_dict)
        roster_data[category] = signed_players
    
    return response_data


@router.put("/{team_id}", response_model=TeamRead)
def update_team(
    *, 
    session: Session = Depends(get_session), 
    team_id: uuid.UUID, 
    team: TeamUpdate,
    current_user: User = Depends(get_current_tournament_admin)
):
    db_team = session.get(Team, team_id)
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # RBAC Check: Tournament Admins can only update teams for THEIR tournament
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if current_user.tournament_id != db_team.tournament_id:
            raise HTTPException(status_code=403, detail="Tournament Admins can only update teams for their assigned tournament")
            
    team_data = team.model_dump(exclude_unset=True)
    
    # Handle tournament update if present
    if "tournament_id" in team_data:
        new_tournament_id = team_data.pop("tournament_id")
        
        # Verify new tournament exists
        new_tournament = session.get(Tournament, new_tournament_id)
        if not new_tournament:
            raise HTTPException(status_code=404, detail="Tournament not found")
            
        # Update foreign key
        db_team.tournament_id = new_tournament_id

        # Also update Standings to reflect the move
        current_standing = session.exec(select(Standing).where(Standing.team_id == team_id)).first()
        if current_standing:
             session.delete(current_standing)
        
        new_standing = Standing(tournament_id=new_tournament_id, team_id=team_id)
        session.add(new_standing)
        
    for key, value in team_data.items():
        setattr(db_team, key, value)
        
    session.add(db_team)
    
    # Audit Log
    record_audit_log(
        session,
        action="UPDATE",
        entity_type="Team",
        entity_id=str(db_team.id),
        description=f"Updated team info: {db_team.name}"
    )

    session.commit()
    session.refresh(db_team)
    
    res = db_team.model_dump()
    res["logo_url"] = get_signed_url(db_team.logo_url)
    return res

@router.delete("/{team_id}")
def delete_team(
    *, 
    session: Session = Depends(get_session), 
    team_id: uuid.UUID,
    current_user: User = Depends(get_current_tournament_admin)
):
    db_team = session.get(Team, team_id)
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    # RBAC Check: Only Super Admins can delete teams
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        raise HTTPException(status_code=403, detail="Tournament Admins cannot delete teams")

    # Audit Log
    record_audit_log(
        session,
        action="DELETE",
        entity_type="Team",
        entity_id=str(team_id),
        description=f"Deleted team: {db_team.name}"
    )

    session.delete(db_team)
    session.commit()
    return {"ok": True}
