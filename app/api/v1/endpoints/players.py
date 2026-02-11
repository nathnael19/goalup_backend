import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.player import Player, PlayerCreate, PlayerRead, PlayerUpdate
from app.models.team import Team
from app.core.audit import record_audit_log

router = APIRouter()

@router.post("/", response_model=PlayerRead)
def create_player(*, session: Session = Depends(get_session), player: PlayerCreate):
    # Manual lowercase to handle any potential Enum/SQLAlchemy mismatch
    player.position = player.position.lower()
    
    # Check if jersey number is unique for the team
    existing_player = session.exec(
        select(Player).where(
            Player.team_id == player.team_id,
            Player.jersey_number == player.jersey_number
        )
    ).first()
    if existing_player:
        raise HTTPException(
            status_code=400,
            detail=f"Jersey number {player.jersey_number} is already taken in this team"
        )
    
    team = session.get(Team, player.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    db_player = Player.model_validate(player)
    session.add(db_player)
    
    # Audit Log
    record_audit_log(
        session,
        action="CREATE",
        entity_type="Player",
        entity_id=str(db_player.id),
        description=f"Created player: {db_player.name} (#{db_player.jersey_number})"
    )

    session.commit()
    session.refresh(db_player)
    return db_player

@router.get("/", response_model=List[PlayerRead])
def read_players(session: Session = Depends(get_session)):
    players = session.exec(select(Player)).all()
    return players

@router.get("/{player_id}", response_model=PlayerRead)
def read_player(*, session: Session = Depends(get_session), player_id: uuid.UUID):
    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

@router.put("/{player_id}", response_model=PlayerRead)
def update_player(
    *, session: Session = Depends(get_session), player_id: uuid.UUID, player: PlayerUpdate
):
    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player_data = player.model_dump(exclude_unset=True)
    
    # Handle position lowercase if provided
    if "position" in player_data and player_data["position"]:
        player_data["position"] = player_data["position"].lower()

    # Check jersey uniqueness if team_id or jersey_number is updated
    if "team_id" in player_data or "jersey_number" in player_data:
        new_team_id = player_data.get("team_id", db_player.team_id)
        new_jersey = player_data.get("jersey_number", db_player.jersey_number)
        
        existing_player = session.exec(
            select(Player).where(
                Player.team_id == new_team_id,
                Player.jersey_number == new_jersey,
                Player.id != player_id
            )
        ).first()
        if existing_player:
            raise HTTPException(
                status_code=400,
                detail=f"Jersey number {new_jersey} is already taken in this team"
            )

    for key, value in player_data.items():
        setattr(db_player, key, value)
    
    session.add(db_player)
    
    # Audit Log
    record_audit_log(
        session,
        action="UPDATE",
        entity_type="Player",
        entity_id=str(db_player.id),
        description=f"Updated player info: {db_player.name}"
    )

    session.commit()
    session.refresh(db_player)
    return db_player

@router.delete("/{player_id}")
def delete_player(*, session: Session = Depends(get_session), player_id: uuid.UUID):
    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")
    # Audit Log
    record_audit_log(
        session,
        action="DELETE",
        entity_type="Player",
        entity_id=str(player_id),
        description=f"Deleted player: {db_player.name}"
    )

    session.delete(db_player)
    session.commit()
    return {"ok": True}
