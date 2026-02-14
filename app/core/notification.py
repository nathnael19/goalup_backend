from typing import Optional
from sqlmodel import Session
from app.models.notification import Notification

def create_notification(
    session: Session,
    title: str,
    message: str,
    notification_type: str,
    link_id: Optional[str] = None
) -> Notification:
    """
    Helper function to create a notification in the database.
    """
    db_notification = Notification(
        title=title,
        message=message,
        type=notification_type,
        link_id=link_id
    )
    session.add(db_notification)
    return db_notification
