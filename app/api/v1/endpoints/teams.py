import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.team import Team, TeamCreate, TeamRead, TeamUpdate, TeamReadWithTournaments, TeamReadDetail
from app.models.standing import Standing
from app.models.tournament import Tournament

router = APIRouter()

@router.post("/", response_model=TeamRead)
def create_team(*, session: Session = Depends(get_session), team: TeamCreate):
    # Verify tournament exists
    tournament = session.get(Tournament, team.tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    # Create team without tournament_id (it's in the payload but not the model)
    team_data = team.model_dump(exclude={"tournament_id"})
    db_team = Team.model_validate(team_data)
    session.add(db_team)
    session.commit()
    session.refresh(db_team)

    # Create initial standing for the team in the tournament
    standing = Standing(tournament_id=team.tournament_id, team_id=db_team.id)
    session.add(standing)
    session.commit()

    # Manually attach tournament_id to response
    team_response = TeamRead.model_validate(db_team)
    team_response.tournament_id = team.tournament_id
    
    return team_response

@router.get("/", response_model=List[TeamRead])
def read_teams(session: Session = Depends(get_session)):
    # Eager load tournaments to avoid N+1 problem
    # Note: We need to import selectinload from sqlalchemy.orm
    from sqlalchemy.orm import selectinload
    query = select(Team).options(selectinload(Team.tournaments))
    teams = session.exec(query).all()
    
    results = []
    for team in teams:
        t_read = TeamRead.model_validate(team)
        if team.tournaments:
            # For now, assign the first found tournament. 
            # In future, logic could select the "active" or "latest" tournament.
            t_read.tournament_id = team.tournaments[0].id
        results.append(t_read)
        
    return results

@router.get("/{team_id}", response_model=TeamReadDetail)
def read_team(*, session: Session = Depends(get_session), team_id: uuid.UUID):
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
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
    
    return response_data

@router.put("/{team_id}", response_model=TeamRead)
def update_team(
    *, session: Session = Depends(get_session), team_id: uuid.UUID, team: TeamUpdate
):
    db_team = session.get(Team, team_id)
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")
    team_data = team.model_dump(exclude_unset=True)
    
    # Handle tournament update if present
    if "tournament_id" in team_data:
        new_tournament_id = team_data.pop("tournament_id")
        
        # Verify new tournament exists
        new_tournament = session.get(Tournament, new_tournament_id)
        if not new_tournament:
            raise HTTPException(status_code=404, detail="Tournament not found")
            
        # Check if actually changing
        # We need to find current tournament assignment.
        # Since we use Standing as link, let's check existing standings
        current_standings = session.exec(select(Standing).where(Standing.team_id == team_id)).all()
        
        # Logic: If updating tournament, we remove old standings to "move" the team
        # This is a hard move - resetting stats in the new tournament context
        for standing in current_standings:
            session.delete(standing)
            
        # Create new standing in new tournament
        new_standing = Standing(tournament_id=new_tournament_id, team_id=team_id)
        session.add(new_standing)
        
    for key, value in team_data.items():
        setattr(db_team, key, value)
        
    session.add(db_team)
    session.commit()
    session.refresh(db_team)
    
    # Manually populate tournament_id for response if it was updated or just fetch it
    # For consistency, let's re-fetch the latest assignment key
    response = TeamRead.model_validate(db_team)
    
    # Fetch current tournament to populate response
    # We can just use the one we set if we updated it, or fetch if not
    # Simpler: just query the standing we just added or existing one
    current_standing = session.exec(select(Standing).where(Standing.team_id == team_id)).first()
    if current_standing:
        response.tournament_id = current_standing.tournament_id
        
    return response

@router.delete("/{team_id}")
def delete_team(
    *, session: Session = Depends(get_session), team_id: uuid.UUID
):
    db_team = session.get(Team, team_id)
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")
    session.delete(db_team)
    session.commit()
    return {"ok": True}
