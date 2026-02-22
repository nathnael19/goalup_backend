import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from app.core.database import get_session
from app.models.match import Match, MatchCreate, MatchRead, MatchUpdate
from app.models.team import Team, TeamRead
from app.models.tournament import Tournament, TournamentRead
from app.models.competition import Competition, CompetitionRead
from app.models.lineup import Lineup, LineupRead, LineupReadWithPlayer
from app.models.goal import Goal, GoalReadWithPlayer
from app.models.card import Card, CardReadWithPlayer
from app.models.substitution import Substitution, SubstitutionReadWithPlayers
from app.api.v1.deps import get_current_active_user, get_current_superuser, get_current_coach, get_current_referee, get_current_match_operator
from app.models.user import User, UserRole, UserRead
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
    referee: Optional[UserRead] = None

@router.post("/", response_model=MatchRead)
def create_match(
    *, 
    session: Session = Depends(get_session), 
    match: MatchCreate,
    current_user: User = Depends(get_current_superuser)
):

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
    tournament_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_active_user)
):
    try:
        query = select(Match).options(
            selectinload(Match.tournament).selectinload(Tournament.competition),
            selectinload(Match.team_a),
            selectinload(Match.team_b),
            selectinload(Match.lineups).selectinload(Lineup.player),
            selectinload(Match.goals_list).selectinload(Goal.player),
            selectinload(Match.goals_list).selectinload(Goal.assistant),
            selectinload(Match.cards_list).selectinload(Card.player),
            selectinload(Match.substitutions).selectinload(Substitution.player_in),
            selectinload(Match.substitutions).selectinload(Substitution.player_out),
            selectinload(Match.referee),
        )

        if current_user.role == UserRole.TOURNAMENT_ADMIN:
            if current_user.tournament_id:
                query = query.where(Match.tournament_id == current_user.tournament_id)
            elif current_user.competition_id:
                query = query.join(Tournament).where(Tournament.competition_id == current_user.competition_id)

        if tournament_id:
            query = query.where(Match.tournament_id == tournament_id)
            
        matches = session.exec(query.offset(offset).limit(limit)).all()
        result = []
        for m in matches:
            em = EnrichedMatchRead.model_validate(m)
            
            # Tournament info (already loaded)
            if m.tournament:
                tournament_dict = TournamentReadWithCompetition.model_validate(m.tournament).model_dump()
                if m.tournament.competition:
                    tournament_dict['competition'] = CompetitionRead.model_validate(m.tournament.competition).model_dump()
                em.tournament = TournamentReadWithCompetition(**tournament_dict)
            
            em.team_a = m.team_a
            em.team_b = m.team_b
            
            # Use pre-loaded relationships
            em.lineups = [LineupReadWithPlayer.model_validate(l) for l in m.lineups]
            em.goals = [GoalReadWithPlayer.model_validate(g) for g in m.goals_list]
            em.cards = [CardReadWithPlayer.model_validate(c) for c in m.cards_list]
            em.substitutions = [SubstitutionReadWithPlayers.model_validate(s) for s in m.substitutions]
            
            result.append(em)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in read_matches: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/{match_id}", response_model=EnrichedMatchRead)
def read_match(
    *, 
    session: Session = Depends(get_session), 
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user)
):
    try:
        query = select(Match).where(Match.id == match_id).options(
            selectinload(Match.tournament).selectinload(Tournament.competition),
            selectinload(Match.team_a),
            selectinload(Match.team_b),
            selectinload(Match.lineups).selectinload(Lineup.player),
            selectinload(Match.goals_list).selectinload(Goal.player),
            selectinload(Match.goals_list).selectinload(Goal.assistant),
            selectinload(Match.cards_list).selectinload(Card.player),
            selectinload(Match.substitutions).selectinload(Substitution.player_in),
            selectinload(Match.substitutions).selectinload(Substitution.player_out),
        )
        # ... rest of the logic
        query = query.where(Match.id == match_id)
        match = session.exec(query).first()
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        
        # RBAC Check
        if current_user.role == UserRole.TOURNAMENT_ADMIN:
            if current_user.tournament_id and match.tournament_id != current_user.tournament_id:
                raise HTTPException(status_code=403, detail="Not authorized to access this match")
            if current_user.competition_id and match.tournament.competition_id != current_user.competition_id:
                raise HTTPException(status_code=403, detail="Not authorized to access this match")
        elif current_user.role == UserRole.REFEREE:
            if match.referee_id != current_user.id:
                 raise HTTPException(status_code=403, detail="Not authorized to access this match as you are not the assigned referee")

        em = EnrichedMatchRead.model_validate(match)
        if match.tournament:
            tournament_dict = TournamentReadWithCompetition.model_validate(match.tournament).model_dump()
            if match.tournament.competition:
                tournament_dict['competition'] = CompetitionRead.model_validate(match.tournament.competition).model_dump()
            em.tournament = TournamentReadWithCompetition(**tournament_dict)
        em.team_a = match.team_a
        em.team_b = match.team_b
        
        em.lineups = [LineupReadWithPlayer.model_validate(l) for l in match.lineups]
        em.goals = [GoalReadWithPlayer.model_validate(g) for g in match.goals_list]
        em.cards = [CardReadWithPlayer.model_validate(c) for c in match.cards_list]
        em.substitutions = [SubstitutionReadWithPlayers.model_validate(s) for s in match.substitutions]
        if match.referee:
            em.referee = UserRead.model_validate(match.referee)
        
        return em
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in read_match({match_id}): {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.put("/{match_id}", response_model=MatchRead)
def update_match(
    *, 
    session: Session = Depends(get_session), 
    match_id: uuid.UUID, 
    match: MatchUpdate,
    current_user: User = Depends(get_current_match_operator)
):
    db_match = session.get(Match, match_id)
    if not db_match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # RBAC Check
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        if current_user.tournament_id != db_match.tournament_id:
            raise HTTPException(status_code=403, detail="Tournament Admins can only update matches for their assigned tournament")
    elif current_user.role == UserRole.REFEREE:
        if db_match.referee_id != current_user.id:
            raise HTTPException(status_code=403, detail="Referees can only update matches they are assigned to")

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
    # RBAC Check: Coaches can only set lineups for THEIR team
    if current_user.role == UserRole.COACH:
        if not current_user.team_id:
             raise HTTPException(status_code=403, detail="Coach user has no assigned team")
        
        # Verify all lineups being set are for the coach's team
        for l in lineups:
            if str(l.team_id) != str(current_user.team_id):
                raise HTTPException(status_code=403, detail="Coaches can only manage their own team's lineup")
    elif current_user.role not in [UserRole.SUPER_ADMIN, UserRole.COACH, UserRole.REFEREE]:
        raise HTTPException(status_code=403, detail="Only coaches, referees, or super admins can set lineups")

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
