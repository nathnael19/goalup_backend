import uuid
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.tournament import Tournament, TournamentCreate, TournamentRead, TournamentUpdate, TournamentReadWithTeams, TournamentScheduleCreate
from app.models.match import Match, MatchStatus

router = APIRouter()

@router.post("/", response_model=TournamentRead)
def create_tournament(*, session: Session = Depends(get_session), tournament: TournamentCreate):
    db_tournament = Tournament.model_validate(tournament)
    session.add(db_tournament)
    session.commit()
    session.refresh(db_tournament)
    return db_tournament

@router.get("/", response_model=List[TournamentRead])
def read_tournaments(session: Session = Depends(get_session)):
    tournaments = session.exec(select(Tournament)).all()
    return tournaments

@router.get("/{tournament_id}", response_model=TournamentReadWithTeams)
def read_tournament(*, session: Session = Depends(get_session), tournament_id: uuid.UUID):
    tournament = session.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournament

@router.put("/{tournament_id}", response_model=TournamentRead)
def update_tournament(
    *, session: Session = Depends(get_session), tournament_id: uuid.UUID, tournament: TournamentUpdate
):
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    tournament_data = tournament.model_dump(exclude_unset=True)
    for key, value in tournament_data.items():
        setattr(db_tournament, key, value)
    session.add(db_tournament)
    session.commit()
    session.refresh(db_tournament)
    return db_tournament

@router.delete("/{tournament_id}")
def delete_tournament(
    *, session: Session = Depends(get_session), tournament_id: uuid.UUID
):
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    session.delete(db_tournament)
    session.commit()
    return {"ok": True}

@router.post("/{tournament_id}/schedule")
def schedule_tournament(
    *, session: Session = Depends(get_session), tournament_id: uuid.UUID, schedule: TournamentScheduleCreate
):
    tournament = session.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    teams = tournament.teams
    if len(teams) < 2:
        raise HTTPException(status_code=400, detail="At least 2 teams are required to schedule a tournament")
    
    # Round Robin Algorithm
    team_ids = [t.id for t in teams]
    if len(team_ids) % 2 != 0:
        team_ids.append(None) # Bye
        
    n = len(team_ids)
    matches = []
    
    # Circle method
    for i in range(n - 1):
        round_matches = []
        for j in range(n // 2):
            t1 = team_ids[j]
            t2 = team_ids[n - 1 - j]
            if t1 is not None and t2 is not None:
                round_matches.append((t1, t2))
        matches.append(round_matches)
        # Rotate all but the first element
        team_ids = [team_ids[0]] + [team_ids[-1]] + team_ids[1:-1]
        
    # Save matches to database
    current_time = schedule.start_date
    match_count = 0
    created_matches = []
    
    for round_idx, round_pairs in enumerate(matches):
        for t1, t2 in round_pairs:
            db_match = Match(
                tournament_id=tournament_id,
                team_a_id=t1,
                team_b_id=t2,
                start_time=current_time,
                status=MatchStatus.scheduled
            )
            session.add(db_match)
            created_matches.append(db_match)
            match_count += 1
            
            if match_count % schedule.matches_per_day == 0:
                current_time += timedelta(days=schedule.interval_days)
                
    session.commit()
    return {"ok": True, "matches_created": len(created_matches)}
