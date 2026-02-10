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
    
    # Check if fixtures already exist for this tournament
    existing_matches = session.exec(
        select(Match).where(Match.tournament_id == tournament_id)
    ).first()
    
    if existing_matches:
        raise HTTPException(
            status_code=400, 
            detail="Fixtures already exist for this tournament. Please delete existing matches before regenerating."
        )
    
    teams = tournament.teams
    if len(teams) < 2:
        raise HTTPException(status_code=400, detail="At least 2 teams are required to schedule a tournament")
    
    # Round Robin Algorithm
    team_ids = [t.id for t in teams]
    if len(team_ids) % 2 != 0:
        team_ids.append(None) # Bye
        
    n = len(team_ids)
    rounds = []
    
    # Generate First Leg (Home vs Away)
    # Circle method
    current_team_ids = list(team_ids)
    for i in range(n - 1):
        round_matches = []
        for j in range(n // 2):
            t1 = current_team_ids[j]
            t2 = current_team_ids[n - 1 - j]
            # If t1 is None, it means t2 has a bye (and vice versa)
            if t1 is not None and t2 is not None:
                # Alternate home/away for fairness or just random?
                # Standard circle method implies:
                if i % 2 == 0:
                    round_matches.append((t1, t2))
                else:
                    round_matches.append((t2, t1))
        rounds.append(round_matches)
        # Rotate all but the first element
        current_team_ids = [current_team_ids[0]] + [current_team_ids[-1]] + current_team_ids[1:-1]

    # Generate Second Leg (Away vs Home)
    # Mirror the first leg matches but swap home/away
    # We append these rounds after the first leg
    second_leg_rounds = []
    for round_matches in rounds:
        new_round = []
        for t1, t2 in round_matches:
            new_round.append((t2, t1))
        second_leg_rounds.append(new_round)
        
    # Combine all rounds
    all_rounds = rounds + second_leg_rounds
        
    # Save matches to database
    current_time = schedule.start_date
    match_count = 0
    created_matches = []
    
    # We want to schedule round by round
    for round_idx, round_pairs in enumerate(all_rounds):
        # All matches in a round happen on the same "interval" day or spread out?
        # Usually a "gameweek" is played on a weekend.
        # Let's increment time PER ROUND, not per match, or respecting matches_per_day
        
        # If matches_per_day is set, we use that to spread fixtures.
        # If it matches team_count/2 (full round per day), then effective interval is per round.
        
        for t1, t2 in round_pairs:
            db_match = Match(
                tournament_id=tournament_id,
                team_a_id=t1,
                team_b_id=t2,
                start_time=current_time,
                status=MatchStatus.scheduled,
                total_time=schedule.total_time
            )
            session.add(db_match)
            created_matches.append(db_match)
            
            # Simple scheduling strategy:
            # Increment time if we've filled the "day" quota
            match_count += 1
            if schedule.matches_per_day > 0 and match_count % schedule.matches_per_day == 0:
                current_time += timedelta(days=schedule.interval_days)

        # If after a round we haven't incremented (because matches_per_day is huge), 
        # we might want to ensure next round is at least next interval?
        # For now, simplistic approach respecting matches_per_day is safer for general use.
        # If user wants 1 round per week: matches_per_day = teams/2, interval = 7.
                
    session.commit()
    return {"ok": True, "matches_created": len(created_matches)}
