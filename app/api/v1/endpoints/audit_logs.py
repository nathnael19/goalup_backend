from typing import List
from fastapi import APIRouter, Depends
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
    limit: int = 50
):
    """Retrieve recent audit log entries."""
    logs = session.exec(
        select(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return logs
