"""
app/schemas/profile.py

Pydantic schemas for the Student Profile module.

Schemas:
  - StudentProfileResponse  : Returned by GET /api/v1/student/profile
  - StudentProfileUpdate    : Accepted by PUT /api/v1/student/profile
"""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────────────────────────────────────
# Profile Response
# ──────────────────────────────────────────────────────────────────────────────
class StudentProfileResponse(BaseModel):
    """
    Full profile returned by GET /api/v1/student/profile.
    Includes all fields plus computed profile completion data.
    Never includes the password hash.
    """

    id: str
    full_name: str
    email: str
    usn: str
    department: str
    role: str
    verification_status: str
    account_status: str
    face_registered: bool

    # Optional — filled during profile completion
    semester: Optional[int]     = None
    section: Optional[str]      = None
    phone: Optional[str]        = None
    gender: Optional[str]       = None
    date_of_birth: Optional[str] = None
    profile_photo: Optional[str] = None

    # Computed
    profile_completed: bool
    profile_completion_pct: int


# ──────────────────────────────────────────────────────────────────────────────
# Profile Update Request
# ──────────────────────────────────────────────────────────────────────────────
class StudentProfileUpdate(BaseModel):
    """
    Fields the student may update via PUT /api/v1/student/profile.
    Department and USN are read-only and excluded here.
    profile_photo is handled separately as a file upload.
    """

    full_name: Optional[str] = Field(
        None, min_length=2, max_length=100,
        description="Full name of the student"
    )
    phone: Optional[str] = Field(
        None, description="10–15 digit phone number"
    )
    semester: Optional[int] = Field(
        None, ge=1, le=8, description="Current semester"
    )
    section: Optional[str] = Field(
        None, min_length=1, max_length=5, description="Section letter (A–D)"
    )
    gender: Optional[Literal["Male", "Female"]] = Field(
        None, description="Gender"
    )
    date_of_birth: Optional[date] = Field(
        None, description="Date of birth (YYYY-MM-DD)"
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.isdigit():
            raise ValueError("Phone number must contain digits only.")
        if not (10 <= len(v) <= 15):
            raise ValueError("Phone number must be between 10 and 15 digits.")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        import re
        if v is None:
            return v
        if not re.match(r"^[A-Za-z\s.'-]+$", v):
            raise ValueError("Full name must contain only letters and spaces.")
        return v.strip()


# ──────────────────────────────────────────────────────────────────────────────
# Profile Update Response
# ──────────────────────────────────────────────────────────────────────────────
class StudentProfileUpdateResponse(BaseModel):
    """Returned after a successful profile update."""

    success: bool
    message: str
    profile_completed: bool
    profile_completion_pct: int
