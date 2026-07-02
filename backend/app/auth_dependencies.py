"""
Shared authentication dependencies for student and teacher routes.

This module centralizes JWT validation, role checks, and account status checks
so the student and teacher modules can share the same authentication flow.
"""

import logging
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.database import get_database
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer()


async def _get_current_user(
    credentials: HTTPAuthorizationCredentials,
    *,
    expected_role: str,
    collection_name: str,
    id_claim: str,
) -> dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise credentials_exception

    if payload.get("role") != expected_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid account role.",
        )

    user_id = payload.get(id_claim)
    if not user_id:
        raise credentials_exception

    from bson import ObjectId

    db = get_database()
    collection = db[collection_name]

    try:
        doc = await collection.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise credentials_exception

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{expected_role.title()} account not found.",
        )

    if doc.get("role") != expected_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid account role.",
        )

    account_status = doc.get("account_status")
    if account_status == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked.",
        )
    if account_status == "inactive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive.",
        )

    if doc.get("is_active") is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive.",
        )

    return doc


async def get_current_student(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict[str, Any]:
    return await _get_current_user(
        credentials,
        expected_role="student",
        collection_name="students",
        id_claim="student_id",
    )


async def get_current_teacher(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict[str, Any]:
    return await _get_current_user(
        credentials,
        expected_role="teacher",
        collection_name="teachers",
        id_claim="teacher_id",
    )
