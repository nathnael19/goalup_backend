import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.notification import Notification, NotificationRead, NotificationUpdate

router = APIRouter()


@router.get("/", response_model=List[NotificationRead])
def read_notifications(
    *,
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: int = 50,
):
    notifications = session.exec(
        select(Notification)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return notifications


@router.patch("/{notification_id}", response_model=NotificationRead)
def update_notification(
    *,
    session: Session = Depends(get_session),
    notification_id: uuid.UUID,
    notification: NotificationUpdate,
):
    db_notification = session.get(Notification, notification_id)
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if notification.is_read is not None:
        db_notification.is_read = notification.is_read
    
    session.add(db_notification)
    session.commit()
    session.refresh(db_notification)
    return db_notification


@router.post("/read-all")
def mark_all_as_read(*, session: Session = Depends(get_session)):
    unread_notifications = session.exec(
        select(Notification).where(Notification.is_read == False)
    ).all()
    for n in unread_notifications:
        n.is_read = True
        session.add(n)
    session.commit()
    return {"ok": True}
