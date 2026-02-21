import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func, SQLModel
from sqlalchemy.orm import selectinload
from app.core.database import get_session
from app.models.standing import Standing, StandingRead
from app.models.match import Match, MatchStatus
from app.models.team import Team, TeamRead
from app.models.tournament import Tournament, TournamentRead
from app.models.user import User, UserRole
from app.api.v1.deps import get_current_active_user

router = APIRouter()

from app.models.competition import CompetitionRead

class TeamStandingRead(StandingRead):
    team: Optional[TeamRead] = None

class TournamentReadWithCompetition(TournamentRead):
    competition: Optional[CompetitionRead] = None

class GroupedTournamentStandings(SQLModel):
    tournament: TournamentReadWithCompetition
    teams: List[TeamStandingRead]

@router.get("/", response_model=List[GroupedTournamentStandings])
def read_standings(
    year: Optional[int] = None, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    query = select(Tournament).options(
        selectinload(Tournament.competition),
        selectinload(Tournament.standings).selectinload(Standing.team),
    )
    
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if current_user.tournament_id:
            query = query.where(Tournament.id == current_user.tournament_id)
        elif current_user.competition_id:
            query = query.where(Tournament.competition_id == current_user.competition_id)
            
    if year:
        query = query.where(Tournament.year == year)
    tournaments = session.exec(query).all()
    result = []
    
    for t in tournaments:
        # Sort standings in Python (already loaded)
        sorted_standings = sorted(
            t.standings,
            key=lambda s: (-s.points, -(s.goals_for - s.goals_against))
        )
        
        team_standings = []
        for s in sorted_standings:
            ts = TeamStandingRead.model_validate(s)
            ts.team = s.team  # Already loaded via selectinload
            team_standings.append(ts)
            
        result.append(GroupedTournamentStandings(
            tournament=TournamentReadWithCompetition.model_validate(t, update={"competition": t.competition}),
            teams=team_standings
        ))
        
    return result

@router.get("/{tournament_id}", response_model=GroupedTournamentStandings)
def get_tournament_standings(
    *, 
    session: Session = Depends(get_session), 
    tournament_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user)
):
    # RBAC Check
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if current_user.tournament_id and current_user.tournament_id != tournament_id:
            raise HTTPException(status_code=403, detail="Not authorized to access these standings")
            
    query = select(Tournament).where(Tournament.id == tournament_id).options(
        selectinload(Tournament.competition),
        selectinload(Tournament.standings).selectinload(Standing.team),
    )
    tournament = session.exec(query).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
        
    if current_user.role == UserRole.TOURNAMENT_ADMIN and current_user.competition_id:
        if tournament.competition_id != current_user.competition_id:
            raise HTTPException(status_code=403, detail="Not authorized to access these standings")
    
    sorted_standings = sorted(
        tournament.standings,
        key=lambda s: (-s.points, -(s.goals_for - s.goals_against))
    )
    
    team_standings = []
    for s in sorted_standings:
        ts = TeamStandingRead.model_validate(s)
        ts.team = s.team
        team_standings.append(ts)
        
    return GroupedTournamentStandings(
        tournament=TournamentReadWithCompetition.model_validate(tournament, update={"competition": tournament.competition}),
        teams=team_standings
    )

@router.post("/{tournament_id}/recalculate")
def recalculate_standings(
    *, 
    session: Session = Depends(get_session), 
    tournament_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user)
):
    tournament = session.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
        
    # RBAC Check
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if current_user.tournament_id and current_user.tournament_id != tournament_id:
             raise HTTPException(status_code=403, detail="Not authorized to recalculate these standings")
        if current_user.competition_id and tournament.competition_id != current_user.competition_id:
             raise HTTPException(status_code=403, detail="Not authorized to recalculate these standings")
    
    # Get all teams in this tournament
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
