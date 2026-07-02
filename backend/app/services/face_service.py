"""
app/services/face_service.py

Business logic for student face registration.
"""

from datetime import datetime
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.models.student import STUDENT_COLLECTION
from app.models.face import FACE_COLLECTION, FaceRegistrationDocument, face_registration_to_dict

async def get_face_status(student_id: str, db: AsyncIOMotorDatabase) -> dict:
    """
    Returns the current face registration status for a student.
    """
    doc = await db[FACE_COLLECTION].find_one({"student_id": student_id})
    if not doc:
        return {
            "status": "Not Registered",
            "images_captured": 0,
            "version": None,
            "registration_date": None,
            "is_registered": False
        }
        
    return {
        "status": "Registered" if doc.get("status") == "active" else "Reset Requested",
        "images_captured": len(doc.get("image_paths", [])),
        "version": doc.get("face_version", 1),
        "registration_date": doc.get("registration_date"),
        "is_registered": True
    }


async def register_face(student_id: str, image_paths: list[str], db: AsyncIOMotorDatabase) -> dict:
    """
    Registers a new face for the student.
    - Creates or replaces the face registration document.
    - Updates the student's face_registered flag.
    """
    # Check if a registration already exists
    existing = await db[FACE_COLLECTION].find_one({"student_id": student_id})
    
    new_version = 1
    if existing:
        new_version = existing.get("face_version", 0) + 1
        
    face_doc = FaceRegistrationDocument(
        student_id=student_id,
        image_paths=image_paths,
        face_version=new_version
    )
    
    doc_dict = face_registration_to_dict(face_doc)
    
    # Upsert the face registration document
    await db[FACE_COLLECTION].update_one(
        {"student_id": student_id},
        {"$set": doc_dict},
        upsert=True
    )
    
    # Update the student document
    result = await db[STUDENT_COLLECTION].update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"face_registered": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Student not found.")
        
    return {
        "message": "Face registration successful.",
        "version": new_version,
        "registration_date": doc_dict["registration_date"]
    }


async def request_face_reset(student_id: str, db: AsyncIOMotorDatabase) -> dict:
    """
    Flags the student's face registration with status 'reset_requested'.
    The admin will perform the actual deletion later.
    """
    existing = await db[FACE_COLLECTION].find_one({"student_id": student_id})
    if not existing:
        raise HTTPException(status_code=404, detail="No face registration found to reset.")
        
    if existing.get("status") == "reset_requested":
        raise HTTPException(status_code=400, detail="A reset request is already pending.")
        
    await db[FACE_COLLECTION].update_one(
        {"student_id": student_id},
        {"$set": {
            "status": "reset_requested",
            "updated_at": datetime.utcnow()
        }}
    )
    
    return {"message": "Face registration reset requested. Please contact the administrator."}
