"""
Teacher authentication service.

This service is intentionally limited to the steps required for authentication:
- find the teacher by email
- verify the password
- verify the active status

JWT creation remains in the shared security helpers and the route layer.
"""

import logging

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import verify_password

logger = logging.getLogger(__name__)


async def authenticate_teacher(
    request,
    db: AsyncIOMotorDatabase,
) -> dict:
    """Authenticate a teacher and return the matching document."""
    collection = db["teachers"]
    teacher = await collection.find_one({"email": request.email})

    if not teacher:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    teacher_role = teacher.get("role")
    if teacher_role and teacher_role != "teacher":
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    if not verify_password(request.password, teacher.get("password_hash", "")):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    if teacher.get("is_active") is False:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive. Please contact the administrator.",
        )

    account_status = teacher.get("account_status")
    if account_status in {"blocked", "inactive"}:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive or blocked. Please contact the administrator.",
        )

    logger.info(f"Teacher authentication successful for {request.email}")
    return teacher
