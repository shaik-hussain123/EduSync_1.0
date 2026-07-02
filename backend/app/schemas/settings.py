"""
app/schemas/settings.py

Pydantic schemas for the Student Settings module.
"""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class StudentSettingsRequest(BaseModel):
    """Fields accepted by PUT /api/v1/student/settings."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, description="10-15 digit phone number")
    gender: Optional[Literal["Male", "Female"]] = Field(None)
    date_of_birth: Optional[date] = Field(None)

    theme: Optional[Literal["light", "dark"]] = Field(None)
    language: Optional[str] = Field(None, max_length=50)
    date_format: Optional[str] = Field(None, max_length=30)
    time_format: Optional[str] = Field(None, max_length=30)
    attendance_notifications: Optional[bool] = Field(None)
    leave_notifications: Optional[bool] = Field(None)
    timetable_notifications: Optional[bool] = Field(None)
    general_notifications: Optional[bool] = Field(None)

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


class StudentPasswordChangeRequest(BaseModel):
    """Fields accepted by PUT /api/v1/student/change-password."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)


class StudentSettingsResponse(BaseModel):
    """Response shape returned for settings GET/PUT requests."""

    success: bool
    message: str
    account: dict
    profile: dict
    preferences: dict
    session: dict


class StudentPasswordChangeResponse(BaseModel):
    """Response shape returned for password change requests."""

    success: bool
    message: str
