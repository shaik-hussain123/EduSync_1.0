"""
app/models/timetable.py

MongoDB document models for the Timetable Module.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional

SUBJECT_COLLECTION = "subjects"
TIMETABLE_COLLECTION = "timetables"

@dataclass
class SubjectDocument:
    subject_id: str
    subject_code: str
    subject_name: str
    department: str
    semester: int
    credits: int
    faculty_id: str
    is_active: bool = field(default=True)
    created_at: datetime = field(default_factory=datetime.utcnow)

def subject_to_dict(doc: SubjectDocument) -> dict:
    return asdict(doc)

@dataclass
class PeriodDocument:
    period_no: int
    start_time: str # "HH:MM" format
    end_time: str # "HH:MM" format
    subject_id: str
    faculty_id: str
    room: str
    is_cancelled: bool = field(default=False)
    cancel_reason: Optional[str] = field(default=None)

@dataclass
class TimetableDocument:
    timetable_id: str
    department: str
    semester: int
    section: str
    day_of_week: str # e.g. "Monday"
    periods: List[PeriodDocument] = field(default_factory=list)
    is_active: bool = field(default=True)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

def timetable_to_dict(doc: TimetableDocument) -> dict:
    # Manual serialization since it contains nested dataclasses
    d = asdict(doc)
    return d
