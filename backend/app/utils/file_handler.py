"""
app/utils/file_handler.py

Reusable file upload utilities for EduSync ERP.

Responsibilities:
  - Validate uploaded file type (MIME / extension).
  - Validate uploaded file size.
  - Save the file to the correct directory with a UUID-based filename.
  - Return the relative path to store in the database.
"""

import uuid
import os
import logging

from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
ALLOWED_IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png"}
MAX_PROFILE_PHOTO_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB

# Base directory for all uploads (relative to the backend/ root when run.py runs)
PROFILE_PHOTOS_DIR = os.path.join("uploads", "profile_photos")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _get_file_extension(filename: str) -> str:
    """Returns the lowercase extension of a filename, e.g. '.jpg'."""
    return os.path.splitext(filename)[1].lower()


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────
async def save_profile_photo(file: UploadFile) -> str:
    """
    Validates and saves a profile photo upload.

    Validations:
        - File extension must be one of: .jpg, .jpeg, .png
        - File size must not exceed 5 MB

    Args:
        file: The UploadFile object from the FastAPI request.

    Returns:
        The relative file path (e.g. 'uploads/profile_photos/uuid.jpg')
        to be stored in MongoDB.

    Raises:
        HTTPException 400: For invalid file type or oversized file.
        HTTPException 500: If the file cannot be saved to disk.
    """
    # ── Validate extension ─────────────────────────────────────────────────
    extension = _get_file_extension(file.filename or "")
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{extension}'. Allowed types: jpg, jpeg, png.",
        )

    # ── Read content and validate size ─────────────────────────────────────
    content = await file.read()
    if len(content) > MAX_PROFILE_PHOTO_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Profile photo exceeds the maximum allowed size of 5 MB.",
        )

    # ── Generate unique filename ───────────────────────────────────────────
    unique_filename = f"{uuid.uuid4().hex}{extension}"
    save_path = os.path.join(PROFILE_PHOTOS_DIR, unique_filename)

    # ── Ensure directory exists ────────────────────────────────────────────
    os.makedirs(PROFILE_PHOTOS_DIR, exist_ok=True)

    # ── Write file to disk ─────────────────────────────────────────────────
    try:
        with open(save_path, "wb") as f:
            f.write(content)
        logger.info(f"Profile photo saved: {save_path}")
    except OSError as e:
        logger.error(f"Failed to save profile photo: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not save profile photo. Please try again.",
        )

    # Return relative path to store in DB (forward slashes for portability)
    return save_path.replace("\\", "/")


async def save_face_images(student_id: str, files: list[UploadFile]) -> list[str]:
    """
    Validates and saves a list of face registration images for a specific student.
    Files are stored in 'uploads/face_registration/{student_id}/'.
    
    Args:
        student_id: The ID (string) of the student.
        files: A list of 8 UploadFile objects.
        
    Returns:
        List of relative file paths saved.
    """
    if len(files) != 8:
        raise HTTPException(
            status_code=400,
            detail=f"Exactly 8 images are required. Received {len(files)}."
        )

    # Base directory for this student's face images
    student_face_dir = os.path.join("uploads", "face_registration", student_id)
    os.makedirs(student_face_dir, exist_ok=True)
    
    saved_paths = []
    
    for i, file in enumerate(files):
        extension = _get_file_extension(file.filename or "")
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type '{extension}' for image {i+1}. Allowed types: jpg, jpeg, png.",
            )
            
        content = await file.read()
        if len(content) > MAX_PROFILE_PHOTO_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Image {i+1} exceeds the maximum allowed size of 5 MB.",
            )
            
        unique_filename = f"{uuid.uuid4().hex}{extension}"
        save_path = os.path.join(student_face_dir, unique_filename)
        
        try:
            with open(save_path, "wb") as f:
                f.write(content)
            saved_paths.append(save_path.replace("\\", "/"))
        except OSError as e:
            logger.error(f"Failed to save face image {i+1} for student {student_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Could not save face image {i+1}. Please try again.",
            )
            
    logger.info(f"Saved 8 face images for student {student_id}")
    return saved_paths
