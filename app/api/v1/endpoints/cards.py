import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.card import Card, CardCreate, CardRead, CardReadWithPlayer
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team
from app.core.audit import record_audit_log

router = APIRouter()

@router.post("/", response_model=CardReadWithPlayer)
def create_card(*, session: Session = Depends(get_session), card: CardCreate):
    # Verify match exists
    match = session.get(Match, card.match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Verify team exists
    team = session.get(Team, card.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
        
    # Verify team belongs to match
    if card.team_id not in [match.team_a_id, match.team_b_id]:
        raise HTTPException(status_code=400, detail="Team does not belong to this match")
        
    # Verify player exists
    player = session.get(Player, card.player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    if player.team_id != card.team_id:
        raise HTTPException(status_code=400, detail="Player does not belong to the recording team")

    db_card = Card.model_validate(card)
    session.add(db_card)
    
    # Update player stats
    if card.type == "yellow":
        player.yellow_cards += 1
    else:
        player.red_cards += 1
    session.add(player)
    
    # Audit Log
    record_audit_log(
        session,
        action="ADD_CARD",
        entity_type="Match",
        entity_id=str(card.match_id),
        description=f"Recorded {card.type} card for player {card.player_id} in match {card.match_id}"
    )

    session.commit()
    session.refresh(db_card)
    return db_card

@router.get("/match/{match_id}", response_model=List[CardReadWithPlayer])
def read_match_cards(*, session: Session = Depends(get_session), match_id: uuid.UUID):
    cards = session.exec(select(Card).where(Card.match_id == match_id).order_by(Card.minute)).all()
    return cards

@router.delete("/{card_id}")
def delete_card(*, session: Session = Depends(get_session), card_id: uuid.UUID):
    db_card = session.get(Card, card_id)
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Revert player stats
    player = session.get(Player, db_card.player_id)
    if player:
        if db_card.type == "yellow":
            player.yellow_cards = max(0, player.yellow_cards - 1)
        else:
            player.red_cards = max(0, player.red_cards - 1)
        session.add(player)
        
    # Audit Log
    record_audit_log(
        session,
        action="DELETE_CARD",
        entity_type="Match",
        entity_id=str(db_card.match_id),
        description=f"Deleted card {card_id} from match {db_card.match_id}"
    )

    session.delete(db_card)
    session.commit()
    return {"ok": True}
