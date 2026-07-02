"""Teacher authentication and attendance routes."""

from fastapi import APIRouter, Body, Depends, status

from app.core.database import get_database
from app.core.security import create_access_token
from app.auth_dependencies import get_current_teacher
from app.schemas.teacher import TeacherLoginRequest, TeacherLoginResponse, TeacherPublicProfile
from app.services.attendance_service import (
    change_session_status,
    get_live_attendance,
    rotate_qr,
    start_session,
)
from app.services.teacher_service import authenticate_teacher

router = APIRouter(prefix="/teacher", tags=["Teacher"])


@router.get("/ping")
async def ping():
    """Confirms the teacher module is registered."""
    return {"module": "teacher", "status": "ready"}


@router.post(
    "/login",
    response_model=TeacherLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Teacher login",
)
async def teacher_login(request: TeacherLoginRequest):
    db = get_database()
    teacher = await authenticate_teacher(request, db)

    teacher_id = str(teacher["_id"])
    token_payload = {
        "teacher_id": teacher_id,
        "email": teacher["email"],
        "role": teacher["role"],
    }
    access_token = create_access_token(token_payload)

    public_profile = TeacherPublicProfile(
        id=teacher_id,
        employee_id=teacher.get("employee_id"),
        full_name=teacher.get("full_name", "Teacher"),
        email=teacher["email"],
        department=teacher.get("department"),
        designation=teacher.get("designation"),
        subjects=teacher.get("subjects", []),
        profile_photo=teacher.get("profile_photo"),
        phone=teacher.get("phone"),
        is_active=teacher.get("is_active", True),
    )

    return TeacherLoginResponse(
        success=True,
        message="Login successful.",
        access_token=access_token,
        token_type="bearer",
        teacher=public_profile,
    )


@router.get("/me", response_model=TeacherPublicProfile)
async def teacher_me(current_teacher: dict = Depends(get_current_teacher)):
    return TeacherPublicProfile(
        id=str(current_teacher["_id"]),
        employee_id=current_teacher.get("employee_id"),
        full_name=current_teacher.get("full_name", "Teacher"),
        email=current_teacher.get("email"),
        department=current_teacher.get("department"),
        designation=current_teacher.get("designation"),
        subjects=current_teacher.get("subjects", []),
        profile_photo=current_teacher.get("profile_photo"),
        phone=current_teacher.get("phone"),
        is_active=current_teacher.get("is_active", True),
    )


@router.post("/logout")
async def teacher_logout():
    return {"success": True, "message": "Teacher logout acknowledged."}


@router.post("/attendance/start", status_code=status.HTTP_201_CREATED)
async def teacher_start_attendance(
    payload: dict = Body(...),
    current_teacher: dict = Depends(get_current_teacher),
):
    db = get_database()
    return await start_session(str(current_teacher["_id"]), payload, db)


@router.post("/attendance/rotate")
async def teacher_rotate_qr(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return await rotate_qr(str(current_teacher["_id"]), db)


@router.post("/attendance/pause")
async def teacher_pause_attendance(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return await change_session_status(str(current_teacher["_id"]), "paused", db)


@router.post("/attendance/resume")
async def teacher_resume_attendance(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return await change_session_status(str(current_teacher["_id"]), "active", db)


@router.post("/attendance/end")
async def teacher_end_attendance(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return await change_session_status(str(current_teacher["_id"]), "ended", db)


@router.get("/attendance/live")
async def teacher_live_attendance(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    records = await get_live_attendance(str(current_teacher["_id"]), db)
    return {"records": records}
