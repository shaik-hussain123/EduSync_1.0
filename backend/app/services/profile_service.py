"""
app/services/profile_service.py

Business logic for the Student Profile module.

Responsibilities:
  - Build StudentProfileResponse from a MongoDB document.
  - Compute profile_completed flag and completion percentage.
  - Apply a profile update dict to the student's MongoDB document.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.student import STUDENT_COLLECTION
from app.schemas.profile import (
    StudentProfileResponse,
    StudentProfileUpdate,
    StudentProfileUpdateResponse,
)
from app.utils.file_handler import save_profile_photo

logger = logging.getLogger(__name__)


# ── Fields that count toward profile completion ───────────────────────────────
COMPLETION_FIELDS = [
    "full_name", "email", "usn", "department",
    "semester", "section", "phone", "gender", "date_of_birth", "profile_photo",
]


def _calc_completion(doc: dict) -> tuple[bool, int]:
    """
    Returns (profile_completed: bool, completion_pct: int) for a student doc.
    """
    filled = [
        f for f in COMPLETION_FIELDS
        if doc.get(f) not in (None, "", [])
    ]
    pct = round(len(filled) / len(COMPLETION_FIELDS) * 100)
    return pct == 100, pct


def _build_profile_response(doc: dict) -> StudentProfileResponse:
    """Converts a raw MongoDB student document to StudentProfileResponse."""
    profile_completed, pct = _calc_completion(doc)
    return StudentProfileResponse(
        id=str(doc["_id"]),
        full_name=doc.get("full_name", ""),
        email=doc.get("email", ""),
        usn=doc.get("usn", ""),
        department=doc.get("department", ""),
        role=doc.get("role", "student"),
        verification_status=doc.get("verification_status", "pending"),
        account_status=doc.get("account_status", "active"),
        face_registered=doc.get("face_registered", False),
        semester=doc.get("semester"),
        section=doc.get("section"),
        phone=doc.get("phone"),
        gender=doc.get("gender"),
        date_of_birth=str(doc["date_of_birth"]) if doc.get("date_of_birth") else None,
        profile_photo=doc.get("profile_photo"),
        profile_completed=profile_completed,
        profile_completion_pct=pct,
    )


# ── GET profile ───────────────────────────────────────────────────────────────
async def get_student_profile(
    student_doc: dict,
) -> StudentProfileResponse:
    """Returns the authenticated student's full profile."""
    return _build_profile_response(student_doc)


# ── PUT profile ───────────────────────────────────────────────────────────────
async def update_student_profile(
    student_doc: dict,
    update_data: StudentProfileUpdate,
    photo_file: Optional[Any],
    db: AsyncIOMotorDatabase,
) -> StudentProfileUpdateResponse:
    """
    Applies allowed field updates to the student's MongoDB document.

    Args:
        student_doc:  The authenticated student's MongoDB document.
        update_data:  Validated StudentProfileUpdate payload.
        photo_file:   Optional UploadFile for a new profile photo.
        db:           Active Motor database instance.

    Returns:
        StudentProfileUpdateResponse with completion metadata.

    Raises:
        HTTPException 500: On unexpected database errors.
    """
    collection = db[STUDENT_COLLECTION]
    student_id = student_doc["_id"]

    # Build the $set payload from non-None update fields
    update_dict: dict = {}

    for field, value in update_data.model_dump(exclude_none=True).items():
        if field == "date_of_birth" and value is not None:
            update_dict["date_of_birth"] = str(value)   # store as "YYYY-MM-DD"
        elif field == "section" and value is not None:
            update_dict["section"] = value.upper()
        else:
            update_dict[field] = value

    # Handle profile photo upload
    if photo_file and photo_file.filename:
        photo_path = await save_profile_photo(photo_file)
        update_dict["profile_photo"] = photo_path

    if not update_dict:
        raise HTTPException(
            status_code=400,
            detail="No fields provided to update.",
        )

    update_dict["updated_at"] = datetime.utcnow()

    # Compute profile_completed after applying the pending changes
    merged = {**student_doc, **update_dict}
    profile_completed, pct = _calc_completion(merged)
    update_dict["profile_completed"] = profile_completed

    try:
        result = await collection.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": update_dict},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Student record not found.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error for student {student_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while saving your profile.",
        )

    logger.info(
        f"Profile updated: student={student_id} | "
        f"fields={list(update_dict.keys())} | completion={pct}%"
    )

    return StudentProfileUpdateResponse(
        success=True,
        message="Profile updated successfully.",
        profile_completed=profile_completed,
        profile_completion_pct=pct,
    )
