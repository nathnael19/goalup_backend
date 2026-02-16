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

from app.core.notification import create_notification

router = APIRouter()

@router.post("/", response_model=NewsRead)
def create_news(
    *, 
    session: Session = Depends(get_session), 
    news: NewsCreate,
    current_user: User = Depends(get_current_news_reporter)
):
    db_news = News.model_validate(news)
    db_news.reporter_id = current_user.id
    session.add(db_news)
    
    # Create notification
    create_notification(
        session,
        title="New Article Published",
        message=f"{db_news.title}",
        notification_type="news",
        link_id=str(db_news.id)
    )
    
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
    
    # Return as NewsRead compatible dict
    news_read = db_news.model_dump()
    news_read["reporter_name"] = current_user.full_name
    return news_read


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
    
    results = []
    for n in news_list:
        n_dict = n.model_dump()
        if n.reporter:
            n_dict["reporter_name"] = n.reporter.full_name
        else:
            n_dict["reporter_name"] = "GoalUp Reporter"
        results.append(n_dict)
            
    return results


@router.get("/{news_id}", response_model=NewsRead)
def read_news_by_id(*, session: Session = Depends(get_session), news_id: uuid.UUID):
    news = session.get(News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News article not found")
    
    if news.reporter:
        reporter_name = news.reporter.full_name
    else:
        reporter_name = "GoalUp Reporter"
        
    res = news.model_dump()
    res["reporter_name"] = reporter_name
    return res


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
    
    res = db_news.model_dump()
    if db_news.reporter:
        res["reporter_name"] = db_news.reporter.full_name
    else:
        res["reporter_name"] = "GoalUp Reporter"
    return res


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
