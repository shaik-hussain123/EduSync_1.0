"""
app/schemas/notification.py

Pydantic schemas for the generic notification module.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field

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


class NotificationItem(BaseModel):
    notification_id: str
    user_id: str
    role: NotificationRole
    title: str
    message: str
    type: NotificationType
    priority: NotificationPriority
    is_read: bool
    action_url: Optional[str] = None
    created_at: str
    read_at: Optional[str] = None


class NotificationListResponse(BaseModel):
    success: bool
    notifications: list[NotificationItem]
    unread_count: int


class UnreadCountResponse(BaseModel):
    success: bool
    unread_count: int


class NotificationActionResponse(BaseModel):
    success: bool
    message: str
    unread_count: int
