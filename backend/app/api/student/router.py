"""
app/api/student/router.py

Student module router.

Endpoints:
  GET  /api/v1/student/ping          — Health check
  GET  /api/v1/student/profile       — Get authenticated student's profile
  PUT  /api/v1/student/profile       — Update authenticated student's profile
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Body

from app.core.database import get_database
from app.dependencies import get_current_student
from app.schemas.profile import (
    StudentProfileResponse,
    StudentProfileUpdate,
    StudentProfileUpdateResponse,
)
from app.schemas.settings import (
    StudentSettingsRequest,
    StudentPasswordChangeRequest,
    StudentSettingsResponse,
    StudentPasswordChangeResponse,
)
from app.services.profile_service import get_student_profile, update_student_profile
from app.services.settings_service import (
    get_student_settings,
    update_student_settings,
    change_student_password,
)
from app.services.attendance_service import scan_qr, get_student_history, get_student_summary
from app.services.timetable_service import get_student_timetable, get_student_timetable_today, get_student_subjects
from app.services.leave_service import get_leave_types, apply_leave, get_student_leave_history, cancel_leave
from app.services.notification_service import (
    list_notifications_for_user,
    get_unread_count,
    mark_notification_read,
    mark_all_notifications_read,
    delete_notification,
)
from app.schemas.notification import NotificationListResponse, UnreadCountResponse, NotificationActionResponse

router = APIRouter(prefix="/student", tags=["Student"])


# ── Health check ──────────────────────────────────────────────────────────────
@router.get("/ping")
async def ping():
    """Confirms the student module is registered and reachable."""
    return {"module": "student", "status": "ready"}


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/student/profile
# Returns the authenticated student's full profile.
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "/profile",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get student profile",
)
async def student_get_profile(
    current_student: dict = Depends(get_current_student),
):
    """
    Returns the authenticated student's full profile including
    optional fields and profile completion percentage.

    **Authentication**: Bearer JWT required.
    """
    return await get_student_profile(current_student)


# ──────────────────────────────────────────────────────────────────────────────
# PUT /api/v1/student/profile
# Updates allowed profile fields. Accepts multipart/form-data for photo upload.
# ──────────────────────────────────────────────────────────────────────────────
@router.put(
    "/profile",
    response_model=StudentProfileUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update student profile",
)
async def student_update_profile(
    # ── Updatable text fields ──────────────────────────────────────────────
    full_name:     Optional[str] = Form(None),
    phone:         Optional[str] = Form(None),
    semester:      Optional[int] = Form(None),
    section:       Optional[str] = Form(None),
    gender:        Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None, description="Format: YYYY-MM-DD"),
    # ── Optional photo ────────────────────────────────────────────────────
    profile_photo: Optional[UploadFile] = File(None),
    # ── Auth dependency ───────────────────────────────────────────────────
    current_student: dict = Depends(get_current_student),
):
    """
    Updates the authenticated student's profile.

    - Accepts **multipart/form-data** (required for photo upload).
    - All fields are optional — send only the fields you want to update.
    - Department and USN are **read-only** and cannot be changed here.
    - Returns updated **profile_completed** flag and **profile_completion_pct**.

    **Authentication**: Bearer JWT required.
    """
    # Parse and validate through Pydantic schema
    from datetime import date as date_type

    dob_parsed = None
    if date_of_birth:
        try:
            dob_parsed = date_type.fromisoformat(date_of_birth)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="date_of_birth must be in YYYY-MM-DD format.",
            )

    try:
        update_data = StudentProfileUpdate(
            full_name=full_name,
            phone=phone,
            semester=semester,
            section=section,
            gender=gender,
            date_of_birth=dob_parsed,
        )
    except Exception as exc:
        errors = json.loads(exc.json()) if hasattr(exc, "json") else str(exc)
        raise HTTPException(status_code=400, detail=errors)

    db = get_database()
    return await update_student_profile(
        student_doc=current_student,
        update_data=update_data,
        photo_file=profile_photo,
        db=db,
    )


# ──────────────────────────────────────────────────────────────────────────────
# ATTENDANCE ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/attendance/scan", status_code=status.HTTP_200_OK)
async def student_scan_attendance(
    payload: dict = Body(...),
    current_student: dict = Depends(get_current_student)
):
    db = get_database()
    qr_token = payload.get("qr_token")
    if not qr_token:
        raise HTTPException(status_code=400, detail="Missing qr_token")
    return await scan_qr(current_student, qr_token, db)


@router.get("/attendance/history")
async def student_attendance_history(
    current_student: dict = Depends(get_current_student)
):
    db = get_database()
    records = await get_student_history(str(current_student["_id"]), db)
    return {"history": records}


@router.get("/attendance/summary")
async def student_attendance_summary(
    current_student: dict = Depends(get_current_student)
):
    db = get_database()
    return await get_student_summary(str(current_student["_id"]), db)


# ──────────────────────────────────────────────────────────────────────────────
# TIMETABLE ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/timetable")
async def student_timetable_all(
    current_student: dict = Depends(get_current_student)
):
    db = get_database()
    timetables = await get_student_timetable(str(current_student["_id"]), db)
    return {"timetables": timetables}


@router.get("/timetable/today")
async def student_timetable_today(
    current_student: dict = Depends(get_current_student)
):
    db = get_database()
    today_schedule = await get_student_timetable_today(str(current_student["_id"]), db)
    return {"today": today_schedule}


@router.get("/subjects")
async def student_subjects_list(
    current_student: dict = Depends(get_current_student)
):
    db = get_database()
    subjects = await get_student_subjects(str(current_student["_id"]), db)
    return {"subjects": subjects}


# ──────────────────────────────────────────────────────────────────────────────
# LEAVE ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/leave/types")
async def student_leave_types():
    db = get_database()
    types = await get_leave_types(db)
    return {"leave_types": types}


@router.post("/leave/apply", status_code=status.HTTP_201_CREATED)
async def student_apply_leave(
    leave_type_id: str = Form(...),
    from_date: str = Form(...),
    to_date: str = Form(...),
    reason: str = Form(...),
    attachment: Optional[UploadFile] = File(None),
    current_student: dict = Depends(get_current_student)
):
    db = get_database()
    return await apply_leave(
        student_id=str(current_student["_id"]),
        leave_type_id=leave_type_id,
        from_date_str=from_date,
        to_date_str=to_date,
        reason=reason,
        attachment=attachment,
        db=db
    )


@router.get("/leave/history")
async def student_leave_history(
    current_student: dict = Depends(get_current_student)
):
    db = get_database()
    history = await get_student_leave_history(str(current_student["_id"]), db)
    return {"history": history}


@router.put("/leave/cancel/{leave_id}")
async def student_cancel_leave(
    leave_id: str,
    current_student: dict = Depends(get_current_student)
):
    db = get_database()
    return await cancel_leave(str(current_student["_id"]), leave_id, db)


# ──────────────────────────────────────────────────────────────────────────────
# SETTINGS ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "/settings",
    response_model=StudentSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get student settings",
)
async def student_get_settings(current_student: dict = Depends(get_current_student)):
    db = get_database()
    return await get_student_settings(current_student, db)


@router.put(
    "/settings",
    response_model=StudentSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update student settings",
)
async def student_update_settings(
    payload: StudentSettingsRequest,
    current_student: dict = Depends(get_current_student),
):
    db = get_database()
    return await update_student_settings(current_student, payload, db)


@router.put(
    "/change-password",
    response_model=StudentPasswordChangeResponse,
    status_code=status.HTTP_200_OK,
    summary="Change student password",
)
async def student_change_password(
    payload: StudentPasswordChangeRequest,
    current_student: dict = Depends(get_current_student),
):
    db = get_database()
    return await change_student_password(current_student, payload, db)


# ──────────────────────────────────────────────────────────────────────────────
# NOTIFICATION ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "/notifications",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get student notifications",
)
async def student_get_notifications(current_student: dict = Depends(get_current_student)):
    db = get_database()
    notifications = await list_notifications_for_user(
        db,
        user_id=str(current_student["_id"]),
        role="student",
    )
    unread_count = await get_unread_count(db, user_id=str(current_student["_id"]), role="student")
    return NotificationListResponse(success=True, notifications=notifications, unread_count=unread_count)


@router.get(
    "/notifications/unread-count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get unread notification count",
)
async def student_get_unread_count(current_student: dict = Depends(get_current_student)):
    db = get_database()
    unread_count = await get_unread_count(db, user_id=str(current_student["_id"]), role="student")
    return UnreadCountResponse(success=True, unread_count=unread_count)


@router.put(
    "/notifications/{notification_id}/read",
    response_model=NotificationActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a notification as read",
)
async def student_mark_notification_read(
    notification_id: str,
    current_student: dict = Depends(get_current_student),
):
    db = get_database()
    return await mark_notification_read(
        db,
        notification_id=notification_id,
        user_id=str(current_student["_id"]),
        role="student",
    )


@router.put(
    "/notifications/read-all",
    response_model=NotificationActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
)
async def student_mark_all_notifications_read(current_student: dict = Depends(get_current_student)):
    db = get_database()
    return await mark_all_notifications_read(
        db,
        user_id=str(current_student["_id"]),
        role="student",
    )


@router.delete(
    "/notifications/{notification_id}",
    response_model=NotificationActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a notification",
)
async def student_delete_notification(
    notification_id: str,
    current_student: dict = Depends(get_current_student),
):
    db = get_database()
    return await delete_notification(
        db,
        notification_id=notification_id,
        user_id=str(current_student["_id"]),
        role="student",
    )



