from typing import List, Optional
from fastapi import APIRouter, Depends, Response
from sqlmodel import Session, select, func
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
    # Build base filter conditions
    conditions = []
    if action:
        conditions.append(AuditLog.action == action)
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if entity_id:
        conditions.append(AuditLog.entity_id == entity_id)

    # Count query
    count_query = select(func.count()).select_from(AuditLog)
    for cond in conditions:
        count_query = count_query.where(cond)
    total = session.exec(count_query).one()

    # Data query
    data_query = select(AuditLog).order_by(AuditLog.timestamp.desc())
    for cond in conditions:
        data_query = data_query.where(cond)
    logs = session.exec(data_query.offset(offset).limit(limit)).all()

    response.headers["X-Total-Count"] = str(total)
    return logs
