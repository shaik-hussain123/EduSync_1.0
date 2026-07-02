"""
app/models/attendance.py

MongoDB document models for the Attendance Module.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

# Collection names
ATTENDANCE_SESSION_COLLECTION = "attendance_sessions"
ATTENDANCE_RECORD_COLLECTION = "attendance_records"

@dataclass
class AttendanceSessionDocument:
    session_id: str
    teacher_id: str
    department: str
    semester: int
    section: str
    subject: str
    room: str
    
    qr_token: str
    token_version: int = field(default=1)
    
    status: str = field(default="active")  # "active", "paused", "ended"
    
    start_time: datetime = field(default_factory=datetime.utcnow)
    expiry_time: Optional[datetime] = field(default=None)
    
    qr_rotation_interval: int = field(default=15)
    max_scan_attempts: int = field(default=3)
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

def session_to_dict(doc: AttendanceSessionDocument) -> dict:
    return asdict(doc)

@dataclass
class AttendanceRecordDocument:
    attendance_id: str
    session_id: str
    student_id: str
    
    attendance_status: str # "Present", "Late", "Absent", "Excused"
    
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    qr_verified: bool = field(default=False)
    wifi_verified: bool = field(default=False)
    face_verified: bool = field(default=False)
    face_match_score: Optional[float] = field(default=None)
    
    device_id: Optional[str] = field(default=None)
    remarks: Optional[str] = field(default=None)

def record_to_dict(doc: AttendanceRecordDocument) -> dict:
    return asdict(doc)
