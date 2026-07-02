from typing import Optional
from fastapi import APIRouter, Body, Depends, File, Form, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

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

@router.put("/profile")
@router.put("/me")
async def update_teacher_profile(
    full_name: Optional[str] = Form(None),
    employee_id: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    designation: Optional[str] = Form(None),
    profile_photo: Optional[UploadFile] = File(None),
    current_teacher: dict = Depends(get_current_teacher),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    updates = {}
    if full_name: updates["full_name"] = full_name.strip()
    if employee_id: updates["employee_id"] = employee_id.strip()
    if phone: updates["phone"] = phone.strip()
    if designation: updates["designation"] = designation.strip()
    
    if profile_photo:
        from app.utils.file_handler import save_profile_photo
        photo_path = await save_profile_photo(profile_photo)
        updates["profile_photo"] = photo_path

    if updates:
        await db["teachers"].update_one(
            {"_id": current_teacher["_id"]},
            {"$set": updates}
        )

    updated_teacher = await db["teachers"].find_one({"_id": current_teacher["_id"]})
    return {
        "success": True,
        "message": "Teacher profile updated successfully.",
        "profile_completion_pct": 100,
        "teacher": {
            "id": str(updated_teacher["_id"]),
            "full_name": updated_teacher.get("full_name"),
            "email": updated_teacher.get("email"),
            "department": updated_teacher.get("department"),
            "phone": updated_teacher.get("phone"),
            "profile_photo": updated_teacher.get("profile_photo")
        }
    }

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

@router.post("/timetable/upsert")
async def teacher_upsert_timetable(
    payload: dict,
    current_teacher: dict = Depends(get_current_teacher),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Allow teacher to add or edit a class period in the timetable."""
    from app.services.timetable_service import upsert_timetable_class
    payload["faculty_id"] = str(current_teacher["_id"])
    return await upsert_timetable_class(payload, db)

@router.get("/timetable")
async def teacher_get_timetable(
    department: str,
    semester: int,
    section: str,
    current_teacher: dict = Depends(get_current_teacher),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Fetch timetable for teacher view."""
    from app.services.timetable_service import get_timetable_by_class
    timetables = await get_timetable_by_class(department, semester, section, db)
    return {"success": True, "timetables": timetables}
