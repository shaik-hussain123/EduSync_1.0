"""
app/models/face.py

MongoDB document model for Face Registration.
Includes fields prepared for future AI embeddings.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Literal

# ──────────────────────────────────────────────────────────────────────────────
# Collection name
# ──────────────────────────────────────────────────────────────────────────────
FACE_COLLECTION = "face_registrations"


# ──────────────────────────────────────────────────────────────────────────────
# Face Registration Document dataclass
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class FaceRegistrationDocument:
    """
    Represents a student's face registration metadata in MongoDB.
    Prepared for future AI integrations (face embeddings).
    """

    student_id: str
    image_paths: List[str]
    face_registered: bool = field(default=True)
    
    # Future AI Integration placeholders
    face_embedding: Optional[List[float]] = field(default=None)
    embedding_model: Optional[str] = field(default=None)
    
    face_version: int = field(default=1)
    
    registration_date: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    status: Literal["active", "reset_requested", "inactive"] = field(default="active")


def face_registration_to_dict(face_doc: FaceRegistrationDocument) -> dict:
    """
    Converts a FaceRegistrationDocument dataclass to a plain dict.
    """
    return asdict(face_doc)
