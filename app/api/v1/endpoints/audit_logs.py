from typing import List, Optional
from fastapi import APIRouter, Depends, Response
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.audit_log import AuditLog, AuditLogRead
from app.api.v1.deps import get_current_superuser
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[AuditLogRead])
def read_audit_logs(
    *, 
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_superuser),
    offset: int = 0, 
    limit: int = 50,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    response: Response,
):
    """Retrieve recent audit log entries."""
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)

    total = session.exec(
        query.with_only_columns(AuditLog.id).order_by(None)
    ).unique().count()

    logs = session.exec(
        query.offset(offset).limit(limit)
    ).all()

    response.headers["X-Total-Count"] = str(total)
    return logs
