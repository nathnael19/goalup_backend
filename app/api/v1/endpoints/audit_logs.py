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
    """Retrieve recent audit log entries (single query with window count)."""
    conditions = []
    if action:
        conditions.append(AuditLog.action == action)
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if entity_id:
        conditions.append(AuditLog.entity_id == entity_id)

    count_over = func.count().over()
    query = (
        select(AuditLog, count_over.label("_total"))
        .order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
    )
    for cond in conditions:
        query = query.where(cond)

    rows = session.exec(query).all()
    total = rows[0][1] if rows else 0
    logs = [row[0] for row in rows]

    response.headers["X-Total-Count"] = str(total)
    return logs
