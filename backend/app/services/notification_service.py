"""
app/services/notification_service.py

Generic notification service for student, teacher, and admin roles.
This module is intentionally role-agnostic so it can be reused later.
"""

import logging
from datetime import datetime
from typing import Any, Literal, Optional

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.notification import (
    NotificationItem,
    NotificationListResponse,
    UnreadCountResponse,
    NotificationActionResponse,
)

logger = logging.getLogger(__name__)

NOTIFICATION_COLLECTION = "notifications"
NotificationRole = Literal["student", "teacher", "admin"]
NotificationPriority = Literal["Low", "Normal", "High", "Critical"]
NotificationType = Literal[
    "Attendance Marked",
    "Attendance Missed",
    "Leave Approved",
    "Leave Rejected",
    "Leave Cancelled",
    "Timetable Updated",
    "Holiday Announcement",
    "Profile Reminder",
    "Face Registration Reminder",
    "General Announcement",
]


def _serialize_notification(doc: dict) -> NotificationItem:
    nid = doc.get("notification_id") or str(doc.get("_id", ""))
    uid = doc.get("user_id") or ""
    created_at = doc.get("created_at")
    if isinstance(created_at, datetime):
        created_at_str = created_at.isoformat()
    else:
        created_at_str = str(created_at or "")

    read_at = doc.get("read_at")
    if isinstance(read_at, datetime):
        read_at_str = read_at.isoformat()
    elif read_at:
        read_at_str = str(read_at)
    else:
        read_at_str = None

    return NotificationItem(
        notification_id=str(nid),
        user_id=str(uid),
        role=doc.get("role", "student"),
        title=doc.get("title", ""),
        message=doc.get("message", ""),
        type=doc.get("type", "General Announcement"),
        priority=doc.get("priority", "Normal"),
        is_read=bool(doc.get("is_read", False)),
        action_url=doc.get("action_url"),
        created_at=created_at_str,
        read_at=read_at_str,
    )


async def create_notification(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    role: NotificationRole,
    title: str,
    message: str,
    notification_type: NotificationType,
    priority: NotificationPriority = "Normal",
    action_url: Optional[str] = None,
) -> NotificationItem:
    collection = db[NOTIFICATION_COLLECTION]
    notification_doc = {
        "notification_id": str(ObjectId()),
        "user_id": str(user_id),
        "role": role,
        "title": title,
        "message": message,
        "type": notification_type,
        "priority": priority,
        "is_read": False,
        "action_url": action_url,
        "created_at": datetime.utcnow(),
        "read_at": None,
    }
    await collection.insert_one(notification_doc)
    return _serialize_notification(notification_doc)


async def list_notifications_for_user(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    role: NotificationRole,
    include_read: bool = True,
    limit: Optional[int] = None,
) -> list[NotificationItem]:
    collection = db[NOTIFICATION_COLLECTION]
    query = {"user_id": str(user_id), "role": role}
    if not include_read:
        query["is_read"] = False

    cursor = collection.find(query).sort("created_at", -1)
    if limit:
        cursor = cursor.limit(limit)
    docs = await cursor.to_list(length=100)

    if not docs and include_read:
        # Seed initial default notifications for fresh users
        if role == "teacher":
            await create_notification(db, user_id=user_id, role=role, title="Attendance reminder", message="2 classes still need session confirmation.", notification_type="Attendance Marked", priority="High")
            await create_notification(db, user_id=user_id, role=role, title="Profile update", message="Keep your department and subjects current.", notification_type="Profile Reminder", priority="Normal")
        elif role == "student":
            await create_notification(db, user_id=user_id, role=role, title="Welcome to EduSync", message="Your student portal is active.", notification_type="General Announcement", priority="Normal")
            await create_notification(db, user_id=user_id, role=role, title="Profile Reminder", message="Please complete your student profile and upload a photo.", notification_type="Profile Reminder", priority="High")
        elif role == "admin":
            await create_notification(db, user_id=user_id, role=role, title="System Overview", message="Admin control panel initialized.", notification_type="General Announcement", priority="Normal")
        
        cursor = collection.find(query).sort("created_at", -1)
        if limit:
            cursor = cursor.limit(limit)
        docs = await cursor.to_list(length=100)

    return [_serialize_notification(doc) for doc in docs]


async def get_unread_count(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    role: NotificationRole,
) -> int:
    collection = db[NOTIFICATION_COLLECTION]
    return await collection.count_documents({"user_id": str(user_id), "role": role, "is_read": False})


async def mark_notification_read(
    db: AsyncIOMotorDatabase,
    *,
    notification_id: str,
    user_id: str,
    role: NotificationRole,
) -> NotificationActionResponse:
    collection = db[NOTIFICATION_COLLECTION]
    result = await collection.update_one(
        {"notification_id": notification_id, "user_id": str(user_id), "role": role},
        {"$set": {"is_read": True, "read_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return NotificationActionResponse(
        success=True,
        message="Notification marked as read.",
        unread_count=await get_unread_count(db, user_id=user_id, role=role),
    )


async def mark_all_notifications_read(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    role: NotificationRole,
) -> NotificationActionResponse:
    collection = db[NOTIFICATION_COLLECTION]
    await collection.update_many(
        {"user_id": str(user_id), "role": role, "is_read": False},
        {"$set": {"is_read": True, "read_at": datetime.utcnow()}},
    )
    return NotificationActionResponse(
        success=True,
        message="All notifications marked as read.",
        unread_count=await get_unread_count(db, user_id=user_id, role=role),
    )


async def delete_notification(
    db: AsyncIOMotorDatabase,
    *,
    notification_id: str,
    user_id: str,
    role: NotificationRole,
) -> NotificationActionResponse:
    collection = db[NOTIFICATION_COLLECTION]
    result = await collection.delete_one({"notification_id": notification_id, "user_id": str(user_id), "role": role})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return NotificationActionResponse(
        success=True,
        message="Notification deleted.",
        unread_count=await get_unread_count(db, user_id=user_id, role=role),
    )
