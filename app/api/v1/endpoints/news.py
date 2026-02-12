import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from datetime import datetime
from app.core.database import get_session
from app.models.news import News, NewsCreate, NewsRead, NewsUpdate, NewsCategory
from app.api.v1.deps import get_current_news_reporter, get_current_superuser
from app.models.user import User
from app.core.audit import record_audit_log

router = APIRouter()


@router.post("/", response_model=NewsRead)
def create_news(
    *, 
    session: Session = Depends(get_session), 
    news: NewsCreate,
    current_user: User = Depends(get_current_news_reporter)
):
    db_news = News.model_validate(news)
    session.add(db_news)
    
    # Audit Log
    record_audit_log(
        session,
        action="CREATE",
        entity_type="News",
        entity_id=str(db_news.id),
        description=f"Published news: {db_news.title}"
    )

    session.commit()
    session.refresh(db_news)
    return db_news


@router.get("/", response_model=List[NewsRead])
def read_news(
    *,
    session: Session = Depends(get_session),
    category: Optional[NewsCategory] = Query(None),
    team_id: Optional[uuid.UUID] = Query(None),
    player_id: Optional[uuid.UUID] = Query(None),
    offset: int = 0,
    limit: int = 100,
):
    query = select(News).order_by(News.created_at.desc())
    if category:
        query = query.where(News.category == category)
    if team_id:
        query = query.where(News.team_id == team_id)
    if player_id:
        query = query.where(News.player_id == player_id)
        
    query = query.offset(offset).limit(limit)
    news_list = session.exec(query).all()
    return news_list


@router.get("/{news_id}", response_model=NewsRead)
def read_news_by_id(*, session: Session = Depends(get_session), news_id: uuid.UUID):
    news = session.get(News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News article not found")
    return news


@router.put("/{news_id}", response_model=NewsRead)
def update_news(
    *, 
    session: Session = Depends(get_session), 
    news_id: uuid.UUID, 
    news: NewsUpdate,
    current_user: User = Depends(get_current_news_reporter)
):
    db_news = session.get(News, news_id)
    if not db_news:
        raise HTTPException(status_code=404, detail="News article not found")
    news_data = news.model_dump(exclude_unset=True)
    news_data["updated_at"] = datetime.utcnow()
    for key, value in news_data.items():
        setattr(db_news, key, value)
    session.add(db_news)
    
    # Audit Log
    record_audit_log(
        session,
        action="UPDATE",
        entity_type="News",
        entity_id=str(db_news.id),
        description=f"Updated news article: {db_news.title}"
    )

    session.commit()
    session.refresh(db_news)
    return db_news


@router.delete("/{news_id}")
def delete_news(
    *, 
    session: Session = Depends(get_session), 
    news_id: uuid.UUID,
    current_user: User = Depends(get_current_news_reporter)
):
    news = session.get(News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News article not found")
    # Audit Log
    record_audit_log(
        session,
        action="DELETE",
        entity_type="News",
        entity_id=str(news_id),
        description=f"Deleted news article: {news.title}"
    )

    session.delete(news)
    session.commit()
    return {"ok": True}
