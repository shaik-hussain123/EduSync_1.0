"""
app/api/settings/router.py

Generic settings router supporting all roles (student, teacher, admin).
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from typing import Optional, Any
from bson import ObjectId

from app.core.database import get_database
from app.auth_dependencies import get_current_user_any
from app.core.security import hash_password, verify_password

router = APIRouter(prefix="/settings", tags=["Settings"])

PREFERENCES_COLLECTION = "user_preferences"


class GenericSettingsUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    theme: Optional[str] = None
    language: Optional[str] = None
    date_format: Optional[str] = None
    time_format: Optional[str] = None
    attendance_notifications: Optional[bool] = None
    leave_notifications: Optional[bool] = None
    timetable_notifications: Optional[bool] = None
    general_notifications: Optional[bool] = None


class GenericPasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


@router.get("")
async def get_generic_settings(
    current_user: dict = Depends(get_current_user_any),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    user_id = str(current_user["_id"])
    role = current_user["role"]

    preferences = await db[PREFERENCES_COLLECTION].find_one({"user_id": user_id})
    if not preferences:
        preferences = {
            "user_id": user_id,
            "theme": "light",
            "language": "English",
            "date_format": "DD/MM/YYYY",
            "time_format": "24h",
            "attendance_notifications": True,
            "leave_notifications": True,
            "timetable_notifications": True,
            "general_notifications": True,
            "updated_at": datetime.utcnow(),
        }
        await db[PREFERENCES_COLLECTION].insert_one(preferences)

    account = {
        "full_name": current_user.get("full_name", ""),
        "email": current_user.get("email", ""),
    }

    if role == "student":
        account["usn"] = current_user.get("usn", "—")
        account["department"] = current_user.get("department", "—")
        account["semester"] = current_user.get("semester", "—")
        account["section"] = current_user.get("section", "—")
    elif role == "teacher":
        account["usn"] = current_user.get("employee_id", "—")
        account["department"] = current_user.get("department", "—")
        account["semester"] = current_user.get("designation", "Faculty")
        account["section"] = "—"
    elif role == "admin":
        account["usn"] = "ADMIN-PORTAL"
        account["department"] = "System Operations"
        account["semester"] = "Root Level"
        account["section"] = "—"

    profile = {
        "full_name": current_user.get("full_name", ""),
        "phone": current_user.get("phone", ""),
        "gender": current_user.get("gender", ""),
        "date_of_birth": current_user.get("date_of_birth", ""),
    }

    session = {
        "login_time": datetime.utcnow().isoformat(),
        "browser": "Chrome / Desktop client",
        "jwt_expiry": "Session token is valid",
    }

    return {
        "success": True,
        "message": "Settings loaded successfully.",
        "account": account,
        "profile": profile,
        "preferences": {
            "theme": preferences.get("theme", "light"),
            "language": preferences.get("language", "English"),
            "date_format": preferences.get("date_format", "DD/MM/YYYY"),
            "time_format": preferences.get("time_format", "24h"),
            "attendance_notifications": preferences.get("attendance_notifications", True),
            "leave_notifications": preferences.get("leave_notifications", True),
            "timetable_notifications": preferences.get("timetable_notifications", True),
            "general_notifications": preferences.get("general_notifications", True),
        },
        "session": session,
    }


@router.put("")
async def update_generic_settings(
    payload: GenericSettingsUpdateRequest,
    current_user: dict = Depends(get_current_user_any),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    user_id = str(current_user["_id"])
    role = current_user["role"]

    if role == "student":
        collection_name = "students"
    elif role == "teacher":
        collection_name = "teachers"
    else:
        collection_name = "admins"

    update_dict: dict[str, Any] = {}
    preference_dict: dict[str, Any] = {}

    for field, value in payload.model_dump(exclude_none=True).items():
        if field in {"full_name", "phone", "gender", "date_of_birth"}:
            update_dict[field] = value
        else:
            preference_dict[field] = value

    if update_dict:
        update_dict["updated_at"] = datetime.utcnow()
        await db[collection_name].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_dict},
        )

    if preference_dict:
        preference_dict["updated_at"] = datetime.utcnow()
        await db[PREFERENCES_COLLECTION].update_one(
            {"user_id": user_id},
            {"$set": preference_dict},
            upsert=True,
        )

    # Refresh user
    refreshed_user = await db[collection_name].find_one({"_id": ObjectId(user_id)})
    refreshed_user["role"] = role

    return await get_generic_settings(refreshed_user, db)


@router.put("/change-password")
async def change_generic_password(
    payload: GenericPasswordChangeRequest,
    current_user: dict = Depends(get_current_user_any),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirm password do not match.")

    user_id = str(current_user["_id"])
    role = current_user["role"]

    if role == "student":
        collection_name = "students"
        password_field = "password"
    elif role == "teacher":
        collection_name = "teachers"
        password_field = "password_hash"
    else:
        collection_name = "admins"
        password_field = "password_hash"

    stored_password = current_user.get(password_field, "")
    if not verify_password(payload.current_password, stored_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    await db[collection_name].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {password_field: hash_password(payload.new_password), "updated_at": datetime.utcnow()}},
    )

    return {"success": True, "message": "Password changed successfully."}
