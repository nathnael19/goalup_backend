import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from datetime import datetime
from app.core.database import get_session
from app.models.news import News, NewsCreate, NewsRead, NewsUpdate, NewsCategory

router = APIRouter()


@router.post("/", response_model=NewsRead)
def create_news(*, session: Session = Depends(get_session), news: NewsCreate):
    db_news = News.model_validate(news)
    session.add(db_news)
    session.commit()
    session.refresh(db_news)
    return db_news


@router.get("/", response_model=List[NewsRead])
def read_news(
    *,
    session: Session = Depends(get_session),
    category: Optional[NewsCategory] = Query(None),
    offset: int = 0,
    limit: int = 100,
):
    query = select(News).order_by(News.created_at.desc())
    if category:
        query = query.where(News.category == category)
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
    *, session: Session = Depends(get_session), news_id: uuid.UUID, news: NewsUpdate
):
    db_news = session.get(News, news_id)
    if not db_news:
        raise HTTPException(status_code=404, detail="News article not found")
    news_data = news.model_dump(exclude_unset=True)
    news_data["updated_at"] = datetime.utcnow()
    for key, value in news_data.items():
        setattr(db_news, key, value)
    session.add(db_news)
    session.commit()
    session.refresh(db_news)
    return db_news


@router.delete("/{news_id}")
def delete_news(*, session: Session = Depends(get_session), news_id: uuid.UUID):
    news = session.get(News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News article not found")
    session.delete(news)
    session.commit()
    return {"ok": True}
