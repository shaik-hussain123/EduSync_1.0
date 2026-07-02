"""
app/models/leave.py

MongoDB document models for the Leave Management Module.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

LEAVE_TYPE_COLLECTION = "leave_types"
LEAVE_REQUEST_COLLECTION = "leave_requests"

@dataclass
class LeaveTypeDocument:
    leave_type_id: str
    name: str
    description: str
    requires_attachment: bool
    max_days: int
    is_active: bool = field(default=True)
    created_at: datetime = field(default_factory=datetime.utcnow)

def leave_type_to_dict(doc: LeaveTypeDocument) -> dict:
    return asdict(doc)

@dataclass
class LeaveRequestDocument:
    leave_id: str
    student_id: str
    leave_type_id: str
    
    from_date: str # "YYYY-MM-DD"
    to_date: str # "YYYY-MM-DD"
    total_days: int
    
    reason: str
    attachment_path: Optional[str] = field(default=None)
    
    status: str = field(default="Pending") # Pending, Approved, Rejected, Cancelled, Completed
    
    teacher_id: Optional[str] = field(default=None)
    admin_id: Optional[str] = field(default=None)
    
    teacher_remarks: Optional[str] = field(default=None)
    admin_remarks: Optional[str] = field(default=None)
    
    approved_at: Optional[datetime] = field(default=None)
    rejected_at: Optional[datetime] = field(default=None)
    cancelled_at: Optional[datetime] = field(default=None)
    
    applied_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

def leave_request_to_dict(doc: LeaveRequestDocument) -> dict:
    return asdict(doc)
