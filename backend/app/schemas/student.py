"""
app/schemas/student.py

Pydantic schemas for the Student module.

Schemas handle:
  - Request validation   (StudentRegisterRequest, StudentLoginRequest)
  - Response formatting  (StudentRegisterResponse, StudentLoginResponse,
                          StudentPublicProfile)

They are NOT database models — see app/models/student.py for that.
"""

import re
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ──────────────────────────────────────────────────────────────────────────────
# Registration Request
# ──────────────────────────────────────────────────────────────────────────────
class StudentRegisterRequest(BaseModel):
    """
    Validates all text fields submitted during student registration.
    The profile_photo (file upload) is handled separately via UploadFile.
    """

    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of the student")
    email: EmailStr = Field(..., description="College email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    confirm_password: str = Field(..., description="Must match password")
    usn: str = Field(..., min_length=3, max_length=20, description="University Seat Number")
    department: str = Field(..., min_length=2, max_length=50, description="Department name (e.g. MCA, CSE)")
    semester: Optional[int] = Field(None, ge=1, le=8, description="Current semester (validated against department)")
    section: Optional[str] = Field(None, min_length=1, max_length=5, description="Section letter (e.g. A, B, C, D)")
    phone: Optional[str] = Field(None, description="10-digit phone number")
    gender: Optional[Literal["Male", "Female"]] = Field(None, description="Gender (Male or Female)")
    date_of_birth: Optional[date] = Field(None, description="Date of birth (YYYY-MM-DD)")

    # ── Field-level validators ─────────────────────────────────────────────
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Phone must be digits only and between 10 and 15 characters."""
        if v is None:
            return v
        if not v.isdigit():
            raise ValueError("Phone number must contain digits only.")
        if not (10 <= len(v) <= 15):
            raise ValueError("Phone number must be between 10 and 15 digits.")
        return v

    @field_validator("usn")
    @classmethod
    def normalise_usn(cls, v: str) -> str:
        """Store USN in uppercase for consistent uniqueness checks."""
        return v.strip().upper()

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Name must not contain numbers or special characters."""
        if not re.match(r"^[A-Za-z\s.'-]+$", v):
            raise ValueError("Full name must contain only letters and spaces.")
        return v.strip()

    # ── Cross-field validators ─────────────────────────────────────────────
    @model_validator(mode="after")
    def passwords_must_match(self) -> "StudentRegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Password and Confirm Password do not match.")
        return self


# ──────────────────────────────────────────────────────────────────────────────
# Registration Response
# ──────────────────────────────────────────────────────────────────────────────
class StudentRegisterResponse(BaseModel):
    """Response returned after a successful student registration."""

    success: bool
    message: str


# ──────────────────────────────────────────────────────────────────────────────
# Login Request
# ──────────────────────────────────────────────────────────────────────────────
class StudentLoginRequest(BaseModel):
    """Validates the student login payload (email + password)."""

    email: EmailStr = Field(..., description="Registered college email")
    password: str = Field(..., min_length=1, description="Account password")


# ──────────────────────────────────────────────────────────────────────────────
# Public Profile (embedded in login response — no sensitive fields)
# ──────────────────────────────────────────────────────────────────────────────
class StudentPublicProfile(BaseModel):
    """
    A safe, public-facing view of a student's profile.
    Never includes password hash or internal MongoDB _id.
    """

    id: str
    full_name: str
    email: str
    usn: str
    department: str
    semester: Optional[int] = None
    section: Optional[str] = None
    verification_status: str
    profile_photo: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Login Response
# ──────────────────────────────────────────────────────────────────────────────
class StudentLoginResponse(BaseModel):
    """Full login response returned on successful authentication."""

    success: bool
    message: str
    access_token: str
    token_type: str = "bearer"
    student: StudentPublicProfile
