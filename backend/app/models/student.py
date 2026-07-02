"""
app/models/student.py

MongoDB document model for a Student.

This module defines:
  - The Python dataclass that maps to the MongoDB 'students' collection.
  - A helper function to convert a dataclass to a MongoDB-ready dict.

We use a plain dataclass instead of Pydantic here because Motor works
directly with Python dicts — no ORM layer is needed.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Literal, Optional


# ──────────────────────────────────────────────────────────────────────────────
# Collection name (single source of truth)
# ──────────────────────────────────────────────────────────────────────────────
STUDENT_COLLECTION = "students"


# ──────────────────────────────────────────────────────────────────────────────
# Student document dataclass
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class StudentDocument:
    """
    Represents a student document stored in MongoDB.
    Every field maps directly to a MongoDB document key.
    """

    full_name: str
    email: str
    password: str                    # bcrypt hash — never plain text
    usn: str
    department: str
    semester: Optional[int] = field(default=None)
    section: Optional[str] = field(default=None)
    phone: Optional[str] = field(default=None)
    gender: Optional[str] = field(default=None)
    date_of_birth: Optional[str] = field(default=None)               # Stored as ISO string "YYYY-MM-DD"
    profile_photo: Optional[str] = field(default=None)               # Relative path: uploads/profile_photos/<uuid>.jpg

    # ── Auto-populated fields ─────────────────────────────────────────────
    role: Literal["student"] = field(default="student")
    verification_status: Literal["pending", "approved", "rejected"] = field(default="pending")
    face_registered: bool = field(default=False)
    profile_completed: bool = field(default=False)          # True when all optional fields are filled
    account_status: Literal["active", "inactive", "blocked"] = field(default="active")
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


def student_to_dict(student: StudentDocument) -> dict:
    """
    Converts a StudentDocument dataclass to a plain dict for MongoDB insertion.
    datetime fields are kept as-is (Motor/PyMongo stores them as BSON Date).
    """
    data = asdict(student)
    return data
