"""
app/api/auth/router.py

Authentication module router.

Endpoints:
  GET  /api/v1/auth/ping                      — Module health check (Sprint 1)
  GET  /api/v1/auth/registration-options      — Dropdown data for registration form (Sprint 2.1.1)
  POST /api/v1/auth/student/register          — Student registration (Sprint 2)
  POST /api/v1/auth/student/login             — Student login / JWT issuance (Sprint 3)
"""

import json

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import date
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_database
from app.schemas.student import (
    StudentRegisterRequest,
    StudentRegisterResponse,
    StudentLoginRequest,
    StudentLoginResponse,
)
from app.services.student_service import register_student
from app.services.auth_service import login_student
from app.services.academic_service import (
    get_active_departments,
    get_valid_sections,
    VALID_GENDERS,
)
from app.utils.file_handler import save_profile_photo

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ──────────────────────────────────────────────────────────────────────────────
# Sprint 1 — Module health check
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/ping")
async def ping():
    """Confirms the auth module is registered and reachable."""
    return {"module": "auth", "status": "ready"}


# ──────────────────────────────────────────────────────────────────────────────
# Sprint 2.1.1 — Registration Options
# GET /api/v1/auth/registration-options
#
# Returns departments, sections, and genders for frontend dropdowns.
# No authentication required — this is a public endpoint.
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "/registration-options",
    summary="Get registration dropdown options",
    tags=["Authentication"],
)
async def registration_options():
    """
    Returns the available departments, sections, and genders
    for populating the student registration form dropdowns.
    """
    db = get_database()
    departments = await get_active_departments(db)
    sections = await get_valid_sections(db)

    return {
        "departments": departments,
        "sections": sections,
        "genders": VALID_GENDERS,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Sprint 2 — Student Registration
# POST /api/v1/auth/student/register
#
# Accepts multipart/form-data because we receive both text fields and a file.
# Pydantic validation is applied manually after extracting Form fields.
# ──────────────────────────────────────────────────────────────────────────────
@router.post(
    "/student/register",
    response_model=StudentRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student",
)
async def student_register(
    # ── Text fields (Form) ─────────────────────────────────────────────────
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    usn: str = Form(...),
    department: str = Form(...),
    semester: Optional[int] = Form(None),
    section: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    date_of_birth: Optional[date] = Form(None, description="Format: YYYY-MM-DD"),
    # ── File field ─────────────────────────────────────────────────────────
    profile_photo: Optional[UploadFile] = File(None, description="Profile photo (jpg/jpeg/png, max 5 MB)"),
):
    """
    Register a new student.

    - Accepts **multipart/form-data** (required for file upload).
    - Validates all fields using the StudentRegisterRequest Pydantic schema.
    - Saves the profile photo to `uploads/profile_photos/`.
    - Hashes the password before storing.
    - Returns **HTTP 201** on success.
    - Returns **HTTP 409** on duplicate email or USN.
    - Returns **HTTP 400** on validation errors.
    """

    # ── Step 1: Run Pydantic validation on all text fields ─────────────────
    # We collect form fields into a dict and parse them through the schema.
    # This gives us all validators (@field_validator, @model_validator) for free.
    try:
        validated = StudentRegisterRequest(
            full_name=full_name,
            email=email,
            password=password,
            confirm_password=confirm_password,
            usn=usn,
            department=department,
            semester=semester,
            section=section,
            phone=phone,
            gender=gender,
            date_of_birth=date_of_birth,
        )
    except Exception as exc:
        # Pydantic raises ValidationError — convert to a clean HTTP 400
        errors = json.loads(exc.json()) if hasattr(exc, "json") else str(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=errors,
        )

    # ── Step 2: Validate and save the profile photo ────────────────────────
    photo_path = await save_profile_photo(profile_photo) if profile_photo else None

    # ── Step 3: Run service (domain check, duplicates, DB insert) ──────────
    db = get_database()
    await register_student(validated, photo_path, db)

    # ── Step 4: Return success response ────────────────────────────────────
    return StudentRegisterResponse(
        success=True,
        message="Student registered successfully. Awaiting admin verification.",
    )

@router.post("/student/debug-register")
async def debug_register():
    from app.core.config import settings
    from app.models.student import STUDENT_COLLECTION
    import os
    db = get_database()
    collection = db[STUDENT_COLLECTION]
    
    # 4. inserted_id
    test_doc = {"debug": "test_student", "email": "debug@college.edu"}
    res = await collection.insert_one(test_doc)
    inserted_id = res.inserted_id
    
    # 5. find_one
    found = await collection.find_one({"_id": inserted_id})
    
    # 6. env check
    env_loaded = "No"
    if os.path.exists(".env"):
        env_loaded = "Yes, .env exists"
    
    return {
        "1_mongodb_uri": settings.MONGODB_URI,
        "2_database_name": settings.DATABASE_NAME,
        "3_collection_name": STUDENT_COLLECTION,
        "4_inserted_id": str(inserted_id),
        "5_document_found": bool(found),
        "6_env_loaded": env_loaded,
        "7_client_nodes": str(db.client.nodes),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Sprint 3 — Student Login
# POST /api/v1/auth/student/login
#
# Accepts JSON (application/json) — no file upload needed for login.
# ──────────────────────────────────────────────────────────────────────────────
@router.post(
    "/student/login",
    response_model=StudentLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Student login",
)
async def student_login(request: StudentLoginRequest):
    """
    Authenticate a student and issue a JWT access token.

    - Accepts **application/json**.
    - Returns **HTTP 200** + JWT on success.
    - Returns **HTTP 401** for invalid email or password.
    - Returns **HTTP 403** for blocked, inactive, or rejected accounts.
    - Pending accounts **can** log in and receive an informational message.
    """
    db = get_database()
    return await login_student(request, db)


class UnifiedLoginRequest(BaseModel):
    role: str
    email: str
    password: str

@router.post("/login")
async def unified_login(payload: UnifiedLoginRequest):
    """
    Unified login endpoint supporting Student, Teacher, and Admin roles.
    """
    db = get_database()
    role = payload.role.lower()
    
    if role == "student":
        from app.schemas.student import StudentLoginRequest
        student_req = StudentLoginRequest(email=payload.email, password=payload.password)
        try:
            res = await login_student(student_req, db)
            student_data = res.student
            if hasattr(student_data, "model_dump"):
                student_dict = student_data.model_dump()
            elif hasattr(student_data, "__dict__"):
                student_dict = student_data.__dict__
            else:
                student_dict = student_data
            return {
                "success": True,
                "redirect": "/student/dashboard",
                "access_token": res.access_token,
                "token_type": res.token_type,
                "student": student_dict
            }
        except HTTPException as e:
            return {
                "success": False,
                "message": e.detail
            }
            
    elif role == "teacher":
        from app.schemas.teacher import TeacherLoginRequest
        from app.services.teacher_service import authenticate_teacher
        teacher_req = TeacherLoginRequest(email=payload.email, password=payload.password)
        try:
            teacher = await authenticate_teacher(teacher_req, db)
            teacher_id = str(teacher["_id"])
            token_payload = {
                "teacher_id": teacher_id,
                "email": teacher["email"],
                "role": "teacher"
            }
            access_token = create_access_token(token_payload)
            return {
                "success": True,
                "redirect": "/teacher/dashboard",
                "access_token": access_token,
                "token_type": "bearer",
                "teacher": {
                    "id": teacher_id,
                    "employee_id": teacher.get("employee_id"),
                    "full_name": teacher.get("full_name", "Teacher"),
                    "email": teacher["email"],
                    "department": teacher.get("department")
                }
            }
        except HTTPException as e:
            return {
                "success": False,
                "message": e.detail
            }
            
    elif role == "admin":
        admin = await db["admins"].find_one({"email": payload.email})
        if not admin or not verify_password(payload.password, admin.get("password_hash", "")):
            return {
                "success": False,
                "message": "Invalid email or password"
            }
        admin_id = str(admin["_id"])
        token_payload = {
            "admin_id": admin_id,
            "email": admin["email"],
            "role": "admin"
        }
        access_token = create_access_token(token_payload)
        return {
            "success": True,
            "redirect": "/admin/dashboard",
            "access_token": access_token,
            "token_type": "bearer",
            "admin": {
                "id": admin_id,
                "full_name": admin.get("full_name", "Admin"),
                "email": admin["email"],
                "role": "admin"
            }
        }
    else:
        return {
            "success": False,
            "message": f"Invalid role: {payload.role}"
        }

