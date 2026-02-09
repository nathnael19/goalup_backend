import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from app.core.database import get_session
from app.models.standing import Standing, StandingRead
from app.models.match import Match, MatchStatus
from app.models.team import Team
from app.models.tournament import Tournament

router = APIRouter()

@router.get("/{tournament_id}", response_model=List[StandingRead])
def get_tournament_standings(*, session: Session = Depends(get_session), tournament_id: uuid.UUID):
    tournament = session.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    standings = session.exec(
        select(Standing).where(Standing.tournament_id == tournament_id).order_by(Standing.points.desc(), (Standing.goals_for - Standing.goals_against).desc())
    ).all()
    
    # Enrich with team names
    result = []
    for s in standings:
        team = session.get(Team, s.team_id)
        sr = StandingRead.model_validate(s)
        sr.team_name = team.name if team else "Unknown"
        result.append(sr)
        
    return result

@router.post("/{tournament_id}/recalculate")
def recalculate_standings(*, session: Session = Depends(get_session), tournament_id: uuid.UUID):
    tournament = session.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Get all teams in this tournament
    # We can get them from the link model or just from matches
    # Better to get them from the tournament.teams relationship
    teams = tournament.teams
    
    # Reset or clear existing standings for this tournament
    existings = session.exec(select(Standing).where(Standing.tournament_id == tournament_id)).all()
    for e in existings:
        session.delete(e)
    session.commit()
    
    # Get all finished matches
    matches = session.exec(
        select(Match).where(Match.tournament_id == tournament_id, Match.status == MatchStatus.finished)
    ).all()
    
    # Stats map: team_id -> dict
    stats = {team.id: {
        "played": 0, "won": 0, "drawn": 0, "lost": 0,
        "goals_for": 0, "goals_against": 0, "points": 0
    } for team in teams}
    
    for m in matches:
        if m.team_a_id not in stats: stats[m.team_a_id] = {"played": 0, "won": 0, "drawn": 0, "lost": 0, "goals_for": 0, "goals_against": 0, "points": 0}
        if m.team_b_id not in stats: stats[m.team_b_id] = {"played": 0, "won": 0, "drawn": 0, "lost": 0, "goals_for": 0, "goals_against": 0, "points": 0}
        
        stats[m.team_a_id]["played"] += 1
        stats[m.team_b_id]["played"] += 1
        stats[m.team_a_id]["goals_for"] += m.score_a
        stats[m.team_a_id]["goals_against"] += m.score_b
        stats[m.team_b_id]["goals_for"] += m.score_b
        stats[m.team_b_id]["goals_against"] += m.score_a
        
        if m.score_a > m.score_b:
            stats[m.team_a_id]["won"] += 1
            stats[m.team_a_id]["points"] += 3
            stats[m.team_b_id]["lost"] += 1
        elif m.score_b > m.score_a:
            stats[m.team_b_id]["won"] += 1
            stats[m.team_b_id]["points"] += 3
            stats[m.team_a_id]["lost"] += 1
        else:
            stats[m.team_a_id]["drawn"] += 1
            stats[m.team_a_id]["points"] += 1
            stats[m.team_b_id]["drawn"] += 1
            stats[m.team_b_id]["points"] += 1
            
    for team_id, s in stats.items():
        db_standing = Standing(
            tournament_id=tournament_id,
            team_id=team_id,
            **s
        )
        session.add(db_standing)
        
    session.commit()
    return {"ok": True, "teams_processed": len(stats)}

@router.get("/", response_model=List[Standing])
def read_standings(session: Session = Depends(get_session)):
    standings = session.exec(select(Standing)).all()
    return standings
