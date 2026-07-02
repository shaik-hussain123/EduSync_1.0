"""
app/services/academic_service.py

Service layer for academic configuration.

Responsibilities:
  - Seed departments and academic_config on startup (idempotent).
  - Fetch active departments.
  - Fetch valid sections from academic_config.
  - Validate department name, semester range, and section during registration.
"""

import logging
from typing import Optional
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException

from app.models.academic import (
    DepartmentDocument,
    AcademicConfigDocument,
    DEPARTMENTS_COLLECTION,
    ACADEMIC_CONFIG_COLLECTION,
    department_to_dict,
    academic_config_to_dict,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Seed data definitions
# ──────────────────────────────────────────────────────────────────────────────
DEPARTMENTS_SEED: list[dict] = [
    {"name": "MCA", "code": "MCA", "total_semesters": 4},
    {"name": "MBA", "code": "MBA", "total_semesters": 4},
    {"name": "CSE", "code": "CSE", "total_semesters": 8},
    {"name": "ISE", "code": "ISE", "total_semesters": 8},
    {"name": "ECE", "code": "ECE", "total_semesters": 8},
    {"name": "EEE", "code": "EEE", "total_semesters": 8},
]

VALID_SECTIONS: list[str] = ["A", "B", "C", "D"]
VALID_GENDERS: list[str] = ["Male", "Female"]


# ──────────────────────────────────────────────────────────────────────────────
# Seeder — called once on application startup
# ──────────────────────────────────────────────────────────────────────────────
async def seed_academic_data(db: AsyncIOMotorDatabase) -> None:
    """
    Seeds the departments and academic_config collections.
    Uses upsert so re-running never creates duplicates.
    Safe to call on every startup.
    """
    dept_col = db[DEPARTMENTS_COLLECTION]
    config_col = db[ACADEMIC_CONFIG_COLLECTION]

    # ── Seed departments ──────────────────────────────────────────────────
    for dept_data in DEPARTMENTS_SEED:
        dept = DepartmentDocument(
            name=dept_data["name"],
            code=dept_data["code"],
            total_semesters=dept_data["total_semesters"],
        )
        await dept_col.update_one(
            {"code": dept.code},                 # filter: match by code
            {"$setOnInsert": department_to_dict(dept)},  # only insert if new
            upsert=True,
        )

    logger.info(f"Departments seeded: {[d['name'] for d in DEPARTMENTS_SEED]}")

    # ── Seed academic_config (sections) ──────────────────────────────────
    sections_config = AcademicConfigDocument(key="sections", value=VALID_SECTIONS)
    await config_col.update_one(
        {"key": "sections"},
        {"$setOnInsert": academic_config_to_dict(sections_config)},
        upsert=True,
    )

    logger.info(f"Academic config seeded: sections={VALID_SECTIONS}")


# ──────────────────────────────────────────────────────────────────────────────
# Getters — used by the registration-options endpoint
# ──────────────────────────────────────────────────────────────────────────────
async def get_active_departments(db: AsyncIOMotorDatabase) -> list[dict]:
    """
    Returns a list of active departments: [{"name": "MCA", "total_semesters": 4}, ...]
    """
    cursor = db[DEPARTMENTS_COLLECTION].find(
        {"active": True},
        {"_id": 0, "name": 1, "total_semesters": 1},
    )
    return await cursor.to_list(length=None)


async def get_valid_sections(db: AsyncIOMotorDatabase) -> list[str]:
    """
    Returns the list of valid sections from academic_config.
    Falls back to the seed constant if the document is missing.
    """
    doc = await db[ACADEMIC_CONFIG_COLLECTION].find_one({"key": "sections"})
    if doc:
        return doc.get("value", VALID_SECTIONS)
    return VALID_SECTIONS


# ──────────────────────────────────────────────────────────────────────────────
# Validators — used by student registration service
# ──────────────────────────────────────────────────────────────────────────────
async def validate_registration_fields(
    department: str,
    semester: Optional[int],
    section: Optional[str],
    db: AsyncIOMotorDatabase,
) -> None:
    """
    Validates department, semester, and section against the database.

    Args:
        department: Department name submitted by the student.
        semester:   Semester number submitted by the student.
        section:    Section letter submitted by the student.
        db:         Active Motor database instance.

    Raises:
        HTTPException 400: If department is invalid/inactive,
                           semester is out of range, or section is invalid.
    """
    # ── 1. Department must exist and be active ────────────────────────────
    dept_doc = await db[DEPARTMENTS_COLLECTION].find_one(
        {"name": {"$regex": f"^{department}$", "$options": "i"}}
    )
    if not dept_doc:
        raise HTTPException(
            status_code=400,
            detail=f"Department '{department}' is not a recognised department.",
        )
    if not dept_doc.get("active", False):
        raise HTTPException(
            status_code=400,
            detail=f"Department '{department}' is currently inactive.",
        )

    # ── 2. Semester must be within department's range ─────────────────────
    if semester is not None:
        total = dept_doc.get("total_semesters", 8)
        if not (1 <= semester <= total):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Semester {semester} is not valid for '{dept_doc['name']}'. "
                    f"Allowed range: 1 – {total}."
                ),
            )

    # ── 3. Section must be in academic_config ─────────────────────────────
    if section is not None:
        valid_sections = await get_valid_sections(db)
        if section.upper() not in [s.upper() for s in valid_sections]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Section '{section}' is not valid. "
                    f"Allowed sections: {', '.join(valid_sections)}."
                ),
            )
