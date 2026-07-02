"""
app/api/notifications/router.py

Notifications module router.
Provides generic notification endpoints for any logged-in role.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.auth_dependencies import get_current_user_any
from app.services.notification_service import (
    list_notifications_for_user,
    get_unread_count,
    mark_notification_read,
    mark_all_notifications_read,
    delete_notification,
)
from app.schemas.notification import (
    NotificationListResponse,
    UnreadCountResponse,
    NotificationActionResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/ping")
async def ping():
    """Temporary health check — confirms the notifications module is registered."""
    return {"module": "notifications", "status": "ready"}


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    current_user: dict = Depends(get_current_user_any),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Retrieve notifications for the currently authenticated user (student/teacher/admin)."""
    user_id = str(current_user["_id"])
    role = current_user["role"]
    
    notifications = await list_notifications_for_user(db, user_id=user_id, role=role)
    unread_count = await get_unread_count(db, user_id=user_id, role=role)
    
    return NotificationListResponse(
        success=True,
        notifications=notifications,
        unread_count=unread_count
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_notifications_unread_count(
    current_user: dict = Depends(get_current_user_any),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get the unread notification count for the logged-in user."""
    user_id = str(current_user["_id"])
    role = current_user["role"]
    unread = await get_unread_count(db, user_id=user_id, role=role)
    return UnreadCountResponse(success=True, unread_count=unread)


@router.put("/{notification_id}/read", response_model=NotificationActionResponse)
async def mark_single_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user_any),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Mark a specific notification as read."""
    user_id = str(current_user["_id"])
    role = current_user["role"]
    return await mark_notification_read(db, notification_id=notification_id, user_id=user_id, role=role)


@router.put("/read-all", response_model=NotificationActionResponse)
async def mark_all_user_notifications_read(
    current_user: dict = Depends(get_current_user_any),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Mark all notifications of the user as read."""
    user_id = str(current_user["_id"])
    role = current_user["role"]
    return await mark_all_notifications_read(db, user_id=user_id, role=role)


@router.delete("/{notification_id}", response_model=NotificationActionResponse)
async def delete_single_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user_any),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Delete a specific notification."""
    user_id = str(current_user["_id"])
    role = current_user["role"]
    return await delete_notification(db, notification_id=notification_id, user_id=user_id, role=role)
