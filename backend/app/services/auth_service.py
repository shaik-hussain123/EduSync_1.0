"""
app/services/auth_service.py

Authentication service for EduSync ERP.

Responsibilities:
  - Look up the student by email.
  - Verify role, account status, and verification status.
  - Verify the password using bcrypt.
  - Issue a JWT access token.
  - Build and return the login response payload.

This service has no knowledge of HTTP routing.
It raises HTTPException so FastAPI propagates the correct status codes.
"""

import logging

from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException

from app.core.security import verify_password, create_access_token
from app.models.student import STUDENT_COLLECTION
from app.schemas.student import StudentLoginRequest, StudentLoginResponse, StudentPublicProfile

logger = logging.getLogger(__name__)


async def login_student(
    request: StudentLoginRequest,
    db: AsyncIOMotorDatabase,
) -> StudentLoginResponse:
    """
    Authenticates a student and returns a JWT access token.

    Steps:
      1. Find student by email.
      2. Confirm role is "student".
      3. Verify password.
      4. Check account_status — block inactive/blocked accounts.
      5. Check verification_status — block rejected accounts.
      6. Generate JWT token.
      7. Return the login response.

    Args:
        request: Validated login credentials.
        db:      Active Motor database instance.

    Returns:
        StudentLoginResponse with token and public profile.

    Raises:
        HTTPException 401: Email not found or wrong password.
        HTTPException 403: Account blocked, inactive, or rejected.
    """
    collection = db[STUDENT_COLLECTION]

    # ── 1. Fetch student by email ─────────────────────────────────────────
    student = await collection.find_one({"email": request.email})

    # ── 2. Email not found — use a generic message to prevent user enumeration
    if not student:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    # ── 3. Role guard — this endpoint is strictly for students
    student_role = student.get("role")
    if student_role and student_role != "student":
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    # ── 4. Password verification ──────────────────────────────────────────
    if not verify_password(request.password, student.get("password", "")):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    # ── 5. Account status check ───────────────────────────────────────────
    account_status = student.get("account_status", "active")

    if account_status == "blocked":
        logger.warning(f"Blocked login attempt: {request.email}")
        raise HTTPException(
            status_code=403,
            detail="Your account has been blocked. Please contact the administrator.",
        )

    if account_status == "inactive":
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive. Please contact the administrator.",
        )

    # ── 6. Verification status check ──────────────────────────────────────
    verification_status = student.get("verification_status", "pending")

    if verification_status == "rejected":
        raise HTTPException(
            status_code=403,
            detail="Your registration has been rejected. Please contact the administrator.",
        )

    # ── 7. Determine login message (pending vs approved) ──────────────────
    if verification_status == "pending":
        message = "Login successful. Your account is awaiting administrator verification."
    else:
        message = "Login successful."

    # ── 8. Build JWT payload ──────────────────────────────────────────────
    student_id = str(student["_id"])

    token_payload = {
        "student_id": student_id,
        "email": student["email"],
        "role": student["role"],
        "usn": student["usn"],
    }

    access_token = create_access_token(token_payload)

    # ── 9. Build public profile (no password, no raw _id) ─────────────────
    public_profile = StudentPublicProfile(
        id=student_id,
        full_name=student["full_name"],
        email=student["email"],
        usn=student["usn"],
        department=student["department"],
        semester=student.get("semester"),
        section=student.get("section"),
        verification_status=verification_status,
        profile_photo=student.get("profile_photo"),
        phone=student.get("phone"),
        gender=student.get("gender"),
        date_of_birth=student.get("date_of_birth"),
    )

    logger.info(
        f"Student login successful: {request.email} | "
        f"Status: {account_status} | Verification: {verification_status}"
    )

    return StudentLoginResponse(
        success=True,
        message=message,
        access_token=access_token,
        token_type="bearer",
        student=public_profile,
    )
