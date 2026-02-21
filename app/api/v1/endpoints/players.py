import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.player import Player, PlayerCreate, PlayerRead, PlayerUpdate
from app.models.team import Team
from app.api.v1.deps import get_current_tournament_admin, get_current_superuser, get_current_active_user
from app.models.user import User, UserRole
from app.core.audit import record_audit_log
from app.core.supabase_client import get_signed_url

router = APIRouter()

@router.post("/", response_model=PlayerRead)
def create_player(
    *, 
    session: Session = Depends(get_session), 
    player: PlayerCreate,
    current_user: User = Depends(get_current_active_user)
):
    # RBAC Check: Coaches can only create for THEIR team
    if current_user.role == UserRole.COACH:
        if not current_user.team_id:
            raise HTTPException(status_code=403, detail="Coach user has no assigned team")
        if player.team_id != current_user.team_id:
            raise HTTPException(status_code=403, detail="Coaches can only create players for their own team")
    elif current_user.role not in []:
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")

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
    
    res = db_player.model_dump()
    res["image_url"] = get_signed_url(db_player.image_url)
    return res

@router.get("/", response_model=List[PlayerRead])
def read_players(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    query = select(Player)
    
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        # Complex join required: Player -> Team -> Tournament
        if current_user.tournament_id:
            query = query.join(Team).where(Team.tournament_id == current_user.tournament_id)
        elif current_user.competition_id:
            query = query.join(Team).join(Tournament).where(Tournament.competition_id == current_user.competition_id)
            
    players = session.exec(query).all()
    results = []
    for p in players:
        p_dict = p.model_dump()
        p_dict["image_url"] = get_signed_url(p.image_url)
        results.append(p_dict)
    return results

@router.get("/{player_id}", response_model=PlayerRead)
def read_player(
    *, 
    session: Session = Depends(get_session), 
    player_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user)
):
    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # RBAC Check
    if current_user.role == UserRole.TOURNAMENT_ADMIN:
        team = session.get(Team, player.team_id)
        if team:
            if current_user.tournament_id and team.tournament_id != current_user.tournament_id:
                raise HTTPException(status_code=403, detail="Not authorized to access this player")
            if current_user.competition_id:
                tournament = session.get(Tournament, team.tournament_id)
                if tournament and tournament.competition_id != current_user.competition_id:
                    raise HTTPException(status_code=403, detail="Not authorized to access this player")
    
    res = player.model_dump()
    res["image_url"] = get_signed_url(player.image_url)
    return res

@router.put("/{player_id}", response_model=PlayerRead)
def update_player(
    *, 
    session: Session = Depends(get_session), 
    player_id: uuid.UUID, 
    player: PlayerUpdate,
    current_user: User = Depends(get_current_active_user)
):
    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # RBAC Check: Coaches can only update THEIR team's players
    if current_user.role == UserRole.COACH:
        if db_player.team_id != current_user.team_id:
            raise HTTPException(status_code=403, detail="Coaches can only update their own team's players")
    elif current_user.role not in []:
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")

    player_data = player.model_dump(exclude_unset=True)
    
    # RBAC: Coaches cannot edit player stats (goals, cards)
    if current_user.role == UserRole.COACH:
        for stat_field in ["goals", "yellow_cards", "red_cards"]:
            if stat_field in player_data:
                player_data.pop(stat_field)
    
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
    
    res = db_player.model_dump()
    res["image_url"] = get_signed_url(db_player.image_url)
    return res

@router.delete("/{player_id}")
def delete_player(
    *, 
    session: Session = Depends(get_session), 
    player_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user)
):
    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")

    # RBAC Check: Coaches can only delete THEIR team's players
    if current_user.role == UserRole.COACH:
        if db_player.team_id != current_user.team_id:
            raise HTTPException(status_code=403, detail="Coaches can only delete their own team's players")
    elif current_user.role not in []:
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")

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
