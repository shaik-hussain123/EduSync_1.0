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
    return NotificationItem(
        notification_id=str(doc["notification_id"]),
        user_id=str(doc["user_id"]),
        role=doc.get("role", "student"),
        title=doc.get("title", ""),
        message=doc.get("message", ""),
        type=doc.get("type", "General Announcement"),
        priority=doc.get("priority", "Normal"),
        is_read=bool(doc.get("is_read", False)),
        action_url=doc.get("action_url"),
        created_at=doc.get("created_at").isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at", "")),
        read_at=(doc.get("read_at").isoformat() if isinstance(doc.get("read_at"), datetime) else str(doc.get("read_at"))) if doc.get("read_at") else None,
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
