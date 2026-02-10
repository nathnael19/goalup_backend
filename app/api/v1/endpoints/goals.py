import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.goal import Goal, GoalCreate, GoalRead, GoalReadWithPlayer
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team

router = APIRouter()

@router.post("/", response_model=GoalReadWithPlayer)
def create_goal(*, session: Session = Depends(get_session), goal: GoalCreate):
    # Verify match and teams exist
    match = session.get(Match, goal.match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Verify team exists
    team = session.get(Team, goal.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
        
    # Verify team belongs to match
    if goal.team_id not in [match.team_a_id, match.team_b_id]:
        raise HTTPException(status_code=400, detail="Team does not belong to this match")
        
    # Verify player exists if provided
    if goal.player_id:
        player = session.get(Player, goal.player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        if player.team_id != goal.team_id:
             # Allowed for own goals? Typically is_own_goal means scored for other team.
             # But usually recorded against the team that got the point.
             # Strategy: team_id is the team that gets the GOAL (point).
             # Scorer is the player. If own goal, scorer team != team_id.
             pass

    db_goal = Goal.model_validate(goal)
    session.add(db_goal)
    
    # Update match score
    if not goal.is_own_goal:
        if goal.team_id == match.team_a_id:
            match.score_a += 1
        else:
            match.score_b += 1
    else:
        # Own goal: Scorer's team gives goal to opponent
        if goal.team_id == match.team_a_id:
             # Team A is the one getting the goal
             match.score_a += 1
        else:
             match.score_b += 1
    
    session.add(match)
    session.commit()
    session.refresh(db_goal)
    return db_goal

@router.get("/match/{match_id}", response_model=List[GoalReadWithPlayer])
def read_match_goals(*, session: Session = Depends(get_session), match_id: uuid.UUID):
    goals = session.exec(select(Goal).where(Goal.match_id == match_id).order_by(Goal.minute)).all()
    return goals

@router.delete("/{goal_id}")
def delete_goal(*, session: Session = Depends(get_session), goal_id: uuid.UUID):
    db_goal = session.get(Goal, goal_id)
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    match = session.get(Match, db_goal.match_id)
    if match:
        # Deduct from score
        if db_goal.team_id == match.team_a_id:
            match.score_a = max(0, match.score_a - 1)
        else:
            match.score_b = max(0, match.score_b - 1)
        session.add(match)
        
    session.delete(db_goal)
    session.commit()
    return {"ok": True}
