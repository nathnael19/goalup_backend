import uuid
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.tournament import Tournament, TournamentCreate, TournamentRead, TournamentUpdate, TournamentReadWithTeams, TournamentScheduleCreate, TournamentKnockoutCreate
from app.models.match import Match, MatchStatus
from app.core.audit import record_audit_log

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
    # Audit Log
    record_audit_log(
        session,
        action="DELETE",
        entity_type="Tournament",
        entity_id=str(tournament_id),
        description=f"Deleted tournament: {db_tournament.name}"
    )

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
                total_time=schedule.total_time,
                match_day=round_idx + 1
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
                
    # Audit Log
    record_audit_log(
        session,
        action="SCHEDULE_GENERATED",
        entity_type="Tournament",
        entity_id=str(tournament_id),
        description=f"Generated {len(created_matches)} fixtures for tournament {tournament_id}"
    )

    session.commit()
    return {"ok": True, "matches_created": len(created_matches)}
@router.post("/{tournament_id}/generate-knockout")
def generate_knockout_fixtures(
    *, session: Session = Depends(get_session), tournament_id: uuid.UUID, schedule: TournamentKnockoutCreate
):
    tournament = session.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Check if fixtures already exist
    existing_matches = session.exec(
        select(Match).where(Match.tournament_id == tournament_id)
    ).first()
    
    if existing_matches:
        raise HTTPException(
            status_code=400, 
            detail="Fixtures already exist. Delete them before regenerating."
        )
    
    teams = tournament.teams
    if len(teams) < 2:
        raise HTTPException(status_code=400, detail="At least 2 teams required")
    
    import math
    import random
    
    team_ids = [t.id for t in teams]
    random.shuffle(team_ids)
    
    t_count = len(team_ids)
    # Next power of 2
    next_pow2 = 2**math.ceil(math.log2(t_count))
    
    # Stages mapping
    stage_names = {
        2: "Final",
        4: "Semi-final",
        8: "Quarter-final",
        16: "Round of 16",
        32: "Round of 32",
        64: "Round of 64"
    }
    
    # For knockout, we only generate the FIRST round that has actual matches.
    # If t_count is 12, next_pow2 is 16.
    # We need 4 matches in Round 1 (8 teams) to get 4 winners.
    # Plus 4 teams with Byes. Total 8 teams in Round 2 (Quarter-finals).
    
    num_matches_r1 = t_count - (next_pow2 // 2)
    # The teams that play in R1
    teams_playing_r1 = team_ids[:num_matches_r1 * 2]
    # The teams with Byes
    teams_with_bye = team_ids[num_matches_r1 * 2:]
    
    current_time = schedule.start_date
    created_matches = []
    
    # Determine stage name
    current_stage_size = next_pow2
    if num_matches_r1 > 0 and next_pow2 > t_count:
        # We have a preliminary round or "First Round"
        stage_name = f"Round of {next_pow2} (Prelim)" if next_pow2 > 8 else "First Round"
    else:
        stage_name = stage_names.get(t_count, f"Round of {t_count}")

    # Generate Round 1 Matches
    for i in range(0, len(teams_playing_r1), 2):
        t1, t2 = teams_playing_r1[i], teams_playing_r1[i+1]
        db_match = Match(
            tournament_id=tournament_id,
            team_a_id=t1,
            team_b_id=t2,
            start_time=current_time,
            status=MatchStatus.scheduled,
            total_time=schedule.total_time,
            match_day=1,
            stage=stage_name
        )
        session.add(db_match)
        created_matches.append(db_match)
        
        # Increment time based on matches_per_day
        if schedule.matches_per_day > 0 and len(created_matches) % schedule.matches_per_day == 0:
            current_time += timedelta(days=schedule.interval_days)

    # Note: For now, we only generate the first round. 
    # Subsequent rounds depend on winners of these matches.
    # The teams_with_bye would enter in the next stage.
    
    # Audit Log
    record_audit_log(
        session,
        action="KNOCKOUT_GENERATED",
        entity_type="Tournament",
        entity_id=str(tournament_id),
        description=f"Generated {len(created_matches)} knockout fixtures for {stage_name}"
    )

    session.commit()
    return {
        "ok": True, 
        "matches_created": len(created_matches), 
        "stage": stage_name,
        "teams_with_bye_ids": [str(tid) for tid in teams_with_bye]
    }
