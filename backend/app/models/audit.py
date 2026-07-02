"""
app/models/audit.py

MongoDB document models for system audit logging.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime

AUDIT_LOG_COLLECTION = "audit_logs"

@dataclass
class AuditLogDocument:
    action: str        # e.g., "admin_login", "student_approved", "student_blocked"
    actor: str         # Email of the person performing the action
    target: str        # The entity/user target of the action
    details: str       # Descriptive information
    timestamp: datetime = field(default_factory=datetime.utcnow)

def audit_log_to_dict(doc: AuditLogDocument) -> dict:
    return asdict(doc)
