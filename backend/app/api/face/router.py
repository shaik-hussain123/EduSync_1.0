"""
app/api/face/router.py

Student Face Registration Router.
"""

from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from app.core.database import get_database
from app.dependencies import get_current_student
from app.utils.file_handler import save_face_images
from app.services.face_service import get_face_status, register_face, request_face_reset

router = APIRouter(prefix="/student/face", tags=["Face Registration"])


@router.get("/status")
async def check_status(current_student: dict = Depends(get_current_student)):
    """Returns the face registration status of the authenticated student."""
    db = get_database()
    return await get_face_status(str(current_student["_id"]), db)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    images: List[UploadFile] = File(...),
    current_student: dict = Depends(get_current_student)
):
    """
    Accepts exactly 8 face images via multipart/form-data.
    Validates, saves the images locally, and updates the database.
    """
    if len(images) != 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exactly 8 images are required. Received {len(images)}."
        )
        
    student_id = str(current_student["_id"])
    
    # Save the images and get the relative paths
    saved_paths = await save_face_images(student_id, images)
    
    # Register the face in the database
    db = get_database()
    return await register_face(student_id, saved_paths, db)


@router.post("/request-reset")
async def request_reset(current_student: dict = Depends(get_current_student)):
    """
    Flags the student's face registration for an admin to reset.
    """
    db = get_database()
    return await request_face_reset(str(current_student["_id"]), db)
