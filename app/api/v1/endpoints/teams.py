import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.team import Team, TeamCreate, TeamRead, TeamUpdate
from app.models.standing import Standing
from app.models.tournament import Tournament

router = APIRouter()

@router.post("/", response_model=TeamRead)
def create_team(*, session: Session = Depends(get_session), team: TeamCreate):
    # Verify tournament exists
    tournament = session.get(Tournament, team.tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    db_team = Team.model_validate(team)
    session.add(db_team)
    session.commit()
    session.refresh(db_team)

    # Create initial standing for the team in the tournament
    standing = Standing(tournament_id=team.tournament_id, team_id=db_team.id)
    session.add(standing)
    session.commit()

    return db_team

@router.get("/", response_model=List[TeamRead])
def read_teams(session: Session = Depends(get_session)):
    teams = session.exec(select(Team)).all()
    return teams

@router.get("/{team_id}", response_model=TeamRead)
def read_team(*, session: Session = Depends(get_session), team_id: uuid.UUID):
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team

@router.put("/{team_id}", response_model=TeamRead)
def update_team(
    *, session: Session = Depends(get_session), team_id: uuid.UUID, team: TeamUpdate
):
    db_team = session.get(Team, team_id)
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")
    team_data = team.model_dump(exclude_unset=True)
    for key, value in team_data.items():
        setattr(db_team, key, value)
    session.add(db_team)
    session.commit()
    session.refresh(db_team)
    return db_team

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
