"""
app/services/student_service.py

Business logic for student registration.

Responsibilities:
  - Validate college email domain.
  - Validate department, semester, and section against the database.
  - Check for duplicate email and USN.
  - Hash the password.
  - Build the StudentDocument.
  - Insert the document into MongoDB.

This layer has NO knowledge of HTTP — it raises HTTPException directly
because FastAPI propagates them automatically from any depth.
"""

import logging
from typing import Optional
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException

from app.core.config import settings
from app.core.security import hash_password
from app.models.student import StudentDocument, STUDENT_COLLECTION, student_to_dict
from app.schemas.student import StudentRegisterRequest
from app.services.academic_service import validate_registration_fields

logger = logging.getLogger(__name__)


async def register_student(
    request: StudentRegisterRequest,
    profile_photo_path: Optional[str],
    db: AsyncIOMotorDatabase,
) -> None:
    """
    Registers a new student in the database.

    Args:
        request:            Validated registration data from the router.
        profile_photo_path: Relative path of the saved profile photo.
        db:                 Active Motor database instance.

    Raises:
        HTTPException 400: Invalid email domain, department, semester, or section.
        HTTPException 409: Duplicate email or USN.
        HTTPException 500: Unexpected database error.
    """
    collection = db[STUDENT_COLLECTION]

    # ── 1. Validate college email domain ──────────────────────────────────
    # TODO: Re-enable college domain validation before production
    # email_domain = request.email.split("@")[-1].lower()
    # if email_domain != settings.COLLEGE_EMAIL_DOMAIN.lower():
    #     raise HTTPException(
    #         status_code=400,
    #         detail=(
    #             f"Only '{settings.COLLEGE_EMAIL_DOMAIN}' email addresses are allowed. "
    #             f"Received domain: '{email_domain}'."
    #         ),
    #     )

    # ── 2. Validate department, semester, and section against the DB ──────
    await validate_registration_fields(
        department=request.department,
        semester=request.semester,
        section=request.section,
        db=db,
    )

    # ── 3. Check duplicate email ──────────────────────────────────────────
    if await collection.find_one({"email": request.email}):
        raise HTTPException(
            status_code=409,
            detail="A student with this email address is already registered.",
        )

    # ── 4. Check duplicate USN ────────────────────────────────────────────
    if await collection.find_one({"usn": request.usn}):
        raise HTTPException(
            status_code=409,
            detail="A student with this USN is already registered.",
        )

    # ── 5. Hash the password ──────────────────────────────────────────────
    hashed = hash_password(request.password)

    # ── 6. Build the MongoDB document ─────────────────────────────────────
    student = StudentDocument(
        full_name=request.full_name,
        email=request.email,
        password=hashed,
        usn=request.usn,
        department=request.department,
        semester=request.semester,
        section=request.section.upper() if request.section else None,          # normalise to uppercase
        phone=request.phone,
        gender=request.gender,
        date_of_birth=str(request.date_of_birth) if request.date_of_birth else None,  # "YYYY-MM-DD"
        profile_photo=profile_photo_path,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # ── 7. Insert into MongoDB ────────────────────────────────────────────
    try:
        await collection.insert_one(student_to_dict(student))
        logger.info(
            f"Student registered: {request.email} | USN: {request.usn} | "
            f"Dept: {request.department}"
        )
    except Exception as e:
        logger.error(f"Database error during student registration: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while saving your registration. Please try again.",
        )
