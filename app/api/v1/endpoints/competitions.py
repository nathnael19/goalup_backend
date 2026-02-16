import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.competition import Competition, CompetitionCreate, CompetitionRead, CompetitionUpdate
from app.core.supabase_client import get_signed_url

router = APIRouter()

@router.post("/", response_model=CompetitionRead)
def create_competition(*, session: Session = Depends(get_session), competition: CompetitionCreate):
    db_competition = Competition.model_validate(competition)
    session.add(db_competition)
    session.commit()
    session.refresh(db_competition)
    
    res = db_competition.model_dump()
    res["image_url"] = get_signed_url(db_competition.image_url)
    return res

@router.get("/", response_model=List[CompetitionRead])
def read_competitions(*, session: Session = Depends(get_session)):
    competitions = session.exec(select(Competition)).all()
    results = []
    for c in competitions:
        c_dict = c.model_dump()
        c_dict["image_url"] = get_signed_url(c.image_url)
        results.append(c_dict)
    return results

@router.get("/{competition_id}", response_model=CompetitionRead)
def read_competition(*, session: Session = Depends(get_session), competition_id: uuid.UUID):
    competition = session.get(Competition, competition_id)
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    
    res = competition.model_dump()
    res["image_url"] = get_signed_url(competition.image_url)
    return res

@router.put("/{competition_id}", response_model=CompetitionRead)
def update_competition(*, session: Session = Depends(get_session), competition_id: uuid.UUID, competition: CompetitionUpdate):
    db_competition = session.get(Competition, competition_id)
    if not db_competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    competition_data = competition.model_dump(exclude_unset=True)
    for key, value in competition_data.items():
        setattr(db_competition, key, value)
    session.add(db_competition)
    session.commit()
    session.refresh(db_competition)
    
    res = db_competition.model_dump()
    res["image_url"] = get_signed_url(db_competition.image_url)
    return res

@router.delete("/{competition_id}")
def delete_competition(*, session: Session = Depends(get_session), competition_id: uuid.UUID):
    competition = session.get(Competition, competition_id)
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    session.delete(competition)
    session.commit()
    return {"ok": True}
