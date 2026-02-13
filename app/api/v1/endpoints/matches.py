import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.match import Match, MatchCreate, MatchRead, MatchUpdate
from app.models.team import Team, TeamRead
from app.models.tournament import Tournament, TournamentRead
from app.models.competition import Competition, CompetitionRead
from app.models.lineup import Lineup, LineupRead, LineupReadWithPlayer
from app.models.goal import Goal, GoalReadWithPlayer
from app.models.card import Card, CardReadWithPlayer
from app.models.substitution import Substitution, SubstitutionReadWithPlayers
from app.api.v1.deps import get_current_active_user, get_current_superuser, get_current_tournament_admin, get_current_coach
from app.models.user import User, UserRole
from app.core.audit import record_audit_log

router = APIRouter()

class TournamentReadWithCompetition(TournamentRead):
    competition: Optional[CompetitionRead] = None

class EnrichedMatchRead(MatchRead):
    tournament: Optional[TournamentReadWithCompetition] = None
    team_a: Optional[TeamRead] = None
    team_b: Optional[TeamRead] = None
    lineups: List[LineupReadWithPlayer] = []
    goals: List[GoalReadWithPlayer] = []
    cards: List[CardReadWithPlayer] = []
    substitutions: List[SubstitutionReadWithPlayers] = []

@router.post("/", response_model=MatchRead)
def create_match(
    *, 
    session: Session = Depends(get_session), 
    match: MatchCreate,
    current_user: User = Depends(get_current_tournament_admin)
):
    # RBAC Check: Tournament Admins can only create matches for THEIR tournament
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if current_user.tournament_id != match.tournament_id:
            raise HTTPException(status_code=403, detail="Tournament Admins can only create matches for their assigned tournament")

    # Verify tournament and teams exist
    tournament = session.get(Tournament, match.tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    team_a = session.get(Team, match.team_a_id)
    team_b = session.get(Team, match.team_b_id)
    if not team_a or not team_b:
        raise HTTPException(status_code=404, detail="One or both teams not found")
        
    db_match = Match.model_validate(match)
    session.add(db_match)
    
    # Audit Log
    record_audit_log(
        session,
        action="CREATE",
        entity_type="Match",
        entity_id=str(db_match.id),
        description=f"Created match: {team_a.name} vs {team_b.name}"
    )
    
    session.commit()
    session.refresh(db_match)
    return db_match

@router.get("/", response_model=List[EnrichedMatchRead])
def read_matches(
    *, 
    session: Session = Depends(get_session), 
    offset: int = 0, 
    limit: int = 100,
    tournament_id: Optional[uuid.UUID] = None
):
    query = select(Match)
    if tournament_id:
        query = query.where(Match.tournament_id == tournament_id)
        
    matches = session.exec(query.offset(offset).limit(limit)).all()
    result = []
    for m in matches:
        em = EnrichedMatchRead.model_validate(m)
        tournament = session.get(Tournament, m.tournament_id)
        if tournament:
            tournament_dict = TournamentReadWithCompetition.model_validate(tournament).model_dump()
            if tournament.competition_id:
                competition = session.get(Competition, tournament.competition_id)
                if competition:
                    tournament_dict['competition'] = CompetitionRead.model_validate(competition).model_dump()
            em.tournament = TournamentReadWithCompetition(**tournament_dict)
        em.team_a = session.get(Team, m.team_a_id)
        em.team_b = session.get(Team, m.team_b_id)
        # Fetch detailed lists
        em.lineups = session.exec(select(Lineup).where(Lineup.match_id == m.id)).all()
        em.goals = session.exec(select(Goal).where(Goal.match_id == m.id)).all()
        em.cards = session.exec(select(Card).where(Card.match_id == m.id)).all()
        em.substitutions = session.exec(select(Substitution).where(Substitution.match_id == m.id)).all()
        result.append(em)
    return result

@router.get("/{match_id}", response_model=EnrichedMatchRead)
def read_match(*, session: Session = Depends(get_session), match_id: uuid.UUID):
    match = session.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    em = EnrichedMatchRead.model_validate(match)
    tournament = session.get(Tournament, match.tournament_id)
    if tournament:
        tournament_dict = TournamentReadWithCompetition.model_validate(tournament).model_dump()
        if tournament.competition_id:
            competition = session.get(Competition, tournament.competition_id)
            if competition:
                tournament_dict['competition'] = CompetitionRead.model_validate(competition).model_dump()
        em.tournament = TournamentReadWithCompetition(**tournament_dict)
    em.team_a = session.get(Team, match.team_a_id)
    em.team_b = session.get(Team, match.team_b_id)
    
    em.lineups = session.exec(select(Lineup).where(Lineup.match_id == match_id)).all()
    em.goals = session.exec(select(Goal).where(Goal.match_id == match_id)).all()
    em.cards = session.exec(select(Card).where(Card.match_id == match_id)).all()
    em.substitutions = session.exec(select(Substitution).where(Substitution.match_id == match_id)).all()
    
    return em

@router.put("/{match_id}", response_model=MatchRead)
def update_match(
    *, 
    session: Session = Depends(get_session), 
    match_id: uuid.UUID, 
    match: MatchUpdate,
    current_user: User = Depends(get_current_tournament_admin)
):
    db_match = session.get(Match, match_id)
    if not db_match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # RBAC Check: Tournament Admins can only update matches for THEIR tournament
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if current_user.tournament_id != db_match.tournament_id:
            raise HTTPException(status_code=403, detail="Tournament Admins can only update matches for their assigned tournament")

    # Lock match data if finished for > 1 hour
    if db_match.status == "finished" and db_match.finished_at:
        import datetime
        lock_time = db_match.finished_at + datetime.timedelta(hours=1)
        if datetime.datetime.now() > lock_time:
            raise HTTPException(
                status_code=403, 
                detail="Match data is locked and cannot be changed after 1 hour of completion"
            )

    match_data = match.model_dump(exclude_unset=True)
    
    # Auto-set finished_at when status becomes finished
    if match_data.get("status") == "finished" and db_match.status != "finished":
        import datetime
        match_data["finished_at"] = datetime.datetime.now()

    # Validate lineup before starting match
    if match_data.get("status") == "live" and db_match.status != "live":
        # Check team A
        team_a_lineup = session.exec(
            select(Lineup).where(
                Lineup.match_id == match_id,
                Lineup.team_id == db_match.team_a_id,
                Lineup.is_starting == True
            )
        ).all()
        # Check team B
        team_b_lineup = session.exec(
            select(Lineup).where(
                Lineup.match_id == match_id,
                Lineup.team_id == db_match.team_b_id,
                Lineup.is_starting == True
            )
        ).all()
        
        if len(team_a_lineup) < 11 or len(team_b_lineup) < 11:
            raise HTTPException(
                status_code=400,
                detail="Starting XI must have at least 11 players for both teams before starting the match"
            )

    for key, value in match_data.items():
        setattr(db_match, key, value)
        
    session.add(db_match)
    
    # Audit Log
    record_audit_log(
        session,
        action="UPDATE",
        entity_type="Match",
        entity_id=str(db_match.id),
        description=f"Updated match info (Status: {db_match.status})"
    )
    
    session.commit()
    session.refresh(db_match)
    return db_match

@router.delete("/{match_id}")
def delete_match(
    *, 
    session: Session = Depends(get_session), 
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_superuser)
):
    match = session.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Audit Log
    record_audit_log(
        session,
        action="DELETE",
        entity_type="Match",
        entity_id=str(match_id),
        description=f"Deleted match: {match.id}"
    )

    session.delete(match)
    session.commit()
    return {"ok": True}

@router.post("/{match_id}/lineups", response_model=List[LineupRead])
def set_lineups(
    *, 
    session: Session = Depends(get_session), 
    match_id: uuid.UUID, 
    lineups: List[Lineup],
    formation_a: Optional[str] = Query(None),
    formation_b: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user)
):
    print(f"DEBUG: set_lineups called by {current_user.email} (Role: {current_user.role}, TeamID: {current_user.team_id}, Type: {type(current_user.team_id)})")
    # RBAC Check: Coaches can only set lineups for THEIR team
    if current_user.role == UserRole.COACH:
        if not current_user.team_id:
             print("DEBUG: Coach has no team_id")
             raise HTTPException(status_code=403, detail="Coach user has no assigned team")
        
        # Verify all lineups being set are for the coach's team
        for l in lineups:
            if str(l.team_id) != str(current_user.team_id):
                print(f"DEBUG: Coach team_id mismatch. Expected {current_user.team_id} ({type(current_user.team_id)}), got {l.team_id} ({type(l.team_id)})")
                raise HTTPException(status_code=403, detail="Coaches can only manage their own team's lineup")
    elif current_user.role not in [UserRole.SUPER_ADMIN, UserRole.TOURNAMENT_ADMIN]:
        print(f"DEBUG: Role {current_user.role} not authorized")
        raise HTTPException(status_code=403, detail="Only coaches or admins can set lineups")

    db_match = session.get(Match, match_id)
    if not db_match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Check lock
    if db_match.status == "finished" and db_match.finished_at:
        import datetime
        lock_time = db_match.finished_at + datetime.timedelta(hours=1)
        if datetime.datetime.now() > lock_time:
            raise HTTPException(
                status_code=403, 
                detail="Match data is locked and cannot be changed after 1 hour of completion"
            )

    # Update formations if provided
    if formation_a is not None:
        # Coaches can only update their own team's formation
        if current_user.role == UserRole.COACH and current_user.team_id != db_match.team_a_id:
            pass  # Silently skip - coach can't set opponent's formation
        else:
            db_match.formation_a = formation_a
    if formation_b is not None:
        if current_user.role == UserRole.COACH and current_user.team_id != db_match.team_b_id:
            pass
        else:
            db_match.formation_b = formation_b

    # Delete existing lineups for this match for teams being updated
    target_team_ids = {l.team_id for l in lineups}
    existing_lineups = session.exec(
        select(Lineup)
        .where(Lineup.match_id == match_id)
        .where(Lineup.team_id.in_(target_team_ids))
    ).all()
    for l in existing_lineups:
        session.delete(l)
    
    # Add new lineups
    for l in lineups:
        l.match_id = match_id
        session.add(l)
        
    # Audit Log
    record_audit_log(
        session,
        action="LINEUP_SET",
        entity_type="Match",
        entity_id=str(match_id),
        description=f"Set lineups for match: {match_id}"
    )

    session.commit()
    return session.exec(select(Lineup).where(Lineup.match_id == match_id)).all()
