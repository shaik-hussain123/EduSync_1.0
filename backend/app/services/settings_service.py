"""
app/services/settings_service.py

Business logic for student settings, preferences, and password changes.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import hash_password, verify_password
from app.models.student import STUDENT_COLLECTION
from app.schemas.settings import (
    StudentSettingsRequest,
    StudentPasswordChangeRequest,
    StudentSettingsResponse,
    StudentPasswordChangeResponse,
)

logger = logging.getLogger(__name__)

PREFERENCES_COLLECTION = "user_preferences"


def _build_preferences_doc(student_id: str, payload: dict) -> dict:
    return {
        "user_id": student_id,
        "theme": payload.get("theme", "light"),
        "language": payload.get("language", "English"),
        "date_format": payload.get("date_format", "DD/MM/YYYY"),
        "time_format": payload.get("time_format", "24h"),
        "attendance_notifications": payload.get("attendance_notifications", True),
        "leave_notifications": payload.get("leave_notifications", True),
        "timetable_notifications": payload.get("timetable_notifications", True),
        "general_notifications": payload.get("general_notifications", True),
        "updated_at": datetime.utcnow(),
    }


async def get_student_settings(student_doc: dict, db: AsyncIOMotorDatabase) -> StudentSettingsResponse:
    student_id = str(student_doc["_id"])
    student_collection = db[STUDENT_COLLECTION]
    preferences_collection = db[PREFERENCES_COLLECTION]

    student = await student_collection.find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found.")

    preferences = await preferences_collection.find_one({"user_id": student_id})
    if not preferences:
        preferences = _build_preferences_doc(student_id, {})
        await preferences_collection.insert_one(preferences)

    account = {
        "full_name": student.get("full_name"),
        "usn": student.get("usn"),
        "email": student.get("email"),
        "department": student.get("department"),
        "semester": student.get("semester"),
        "section": student.get("section"),
    }
    profile = {
        "full_name": student.get("full_name"),
        "phone": student.get("phone"),
        "gender": student.get("gender"),
        "date_of_birth": student.get("date_of_birth"),
    }
    session = {
        "login_time": student.get("updated_at"),
        "browser": "Unknown",
        "jwt_expiry": "Session token expires according to server settings",
    }

    return StudentSettingsResponse(
        success=True,
        message="Settings loaded successfully.",
        account=account,
        profile=profile,
        preferences={
            "theme": preferences.get("theme", "light"),
            "language": preferences.get("language", "English"),
            "date_format": preferences.get("date_format", "DD/MM/YYYY"),
            "time_format": preferences.get("time_format", "24h"),
            "attendance_notifications": preferences.get("attendance_notifications", True),
            "leave_notifications": preferences.get("leave_notifications", True),
            "timetable_notifications": preferences.get("timetable_notifications", True),
            "general_notifications": preferences.get("general_notifications", True),
        },
        session=session,
    )


async def update_student_settings(
    student_doc: dict,
    payload: StudentSettingsRequest,
    db: AsyncIOMotorDatabase,
) -> StudentSettingsResponse:
    student_id = str(student_doc["_id"])
    student_collection = db[STUDENT_COLLECTION]
    preferences_collection = db[PREFERENCES_COLLECTION]

    student = await student_collection.find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found.")

    update_dict: dict[str, Any] = {}
    for field, value in payload.model_dump(exclude_none=True).items():
        if field in {"full_name", "phone", "gender", "date_of_birth"}:
            if field == "full_name" and value is not None:
                update_dict[field] = value
            elif field == "phone" and value is not None:
                update_dict[field] = value
            elif field == "gender" and value is not None:
                update_dict[field] = value
            elif field == "date_of_birth" and value is not None:
                update_dict[field] = str(value)
        else:
            update_dict[field] = value

    if update_dict:
        preference_fields = {k: v for k, v in update_dict.items() if k not in {"full_name", "phone", "gender", "date_of_birth"}}
        if preference_fields:
            preferences_doc = _build_preferences_doc(student_id, preference_fields)
            preferences_doc["updated_at"] = datetime.utcnow()
            await preferences_collection.update_one(
                {"user_id": student_id},
                {"$set": preferences_doc},
                upsert=True,
            )

        profile_fields = {k: v for k, v in update_dict.items() if k in {"full_name", "phone", "gender", "date_of_birth"}}
        if profile_fields:
            profile_fields["updated_at"] = datetime.utcnow()
            await student_collection.update_one(
                {"_id": ObjectId(student_id)},
                {"$set": profile_fields},
            )

    return await get_student_settings(student_doc, db)


async def change_student_password(
    student_doc: dict,
    payload: StudentPasswordChangeRequest,
    db: AsyncIOMotorDatabase,
) -> StudentPasswordChangeResponse:
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirm password do not match.")

    student_id = str(student_doc["_id"])
    collection = db[STUDENT_COLLECTION]
    student = await collection.find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found.")

    if not verify_password(payload.current_password, student.get("password", "")):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    await collection.update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"password": hash_password(payload.new_password), "updated_at": datetime.utcnow()}},
    )

    return StudentPasswordChangeResponse(success=True, message="Password changed successfully.")
