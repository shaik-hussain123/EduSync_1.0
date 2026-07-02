"""
Pydantic schemas for teacher authentication and profile responses.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class TeacherLoginRequest(BaseModel):
    """Validates the teacher login payload."""

    email: EmailStr = Field(..., description="Registered teacher email")
    password: str = Field(..., min_length=1, description="Account password")


class TeacherPublicProfile(BaseModel):
    """Safe teacher profile data returned to the client."""

    id: str
    employee_id: Optional[str] = None
    full_name: str
    email: str
    department: Optional[str] = None
    designation: Optional[str] = None
    subjects: list[str] = Field(default_factory=list)
    profile_photo: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True


class TeacherLoginResponse(BaseModel):
    """Response returned after a successful teacher login."""

    success: bool
    message: str
    access_token: str
    token_type: str = "bearer"
    teacher: TeacherPublicProfile
