from typing import Optional
from sqlmodel import Session
from app.models.notification import Notification
from app.core.config import settings
import httpx

def create_notification(
    session: Session,
    title: str,
    message: str,
    notification_type: str,
    link_id: Optional[str] = None
) -> Notification:
    """
    Helper function to create a notification in the database and optionally
    send it to an external push/notification system via webhook.
    """
    db_notification = Notification(
        title=title,
        message=message,
        type=notification_type,
        link_id=link_id
    )
    session.add(db_notification)

    # Optional push webhook
    if settings.PUSH_WEBHOOK_URL:
        try:
            with httpx.Client(timeout=2.0) as client:
                client.post(
                    settings.PUSH_WEBHOOK_URL,
                    json={
                        "title": title,
                        "message": message,
                        "type": notification_type,
                        "link_id": link_id,
                    },
                )
        except Exception:
            # Best-effort: do not break API if webhook fails
            pass

    return db_notification
