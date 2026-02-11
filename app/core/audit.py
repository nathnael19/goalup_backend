from datetime import datetime
from sqlmodel import Session
from app.models.audit_log import AuditLog

def record_audit_log(
    session: Session,
    action: str,
    entity_type: str,
    entity_id: str,
    description: str
):
    """
    Utility function to record an administrative action in the audit log.
    """
    db_log = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        timestamp=datetime.utcnow()
    )
    session.add(db_log)
    # We don't commit here to allow it to be part of the caller's transaction
