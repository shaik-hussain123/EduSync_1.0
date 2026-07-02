"""
app/models/academic.py

MongoDB document models for academic configuration.

Collections:
  - departments     : Stores department records (MCA, CSE, etc.)
  - academic_config : Stores global config values (valid sections, etc.)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Literal

# ──────────────────────────────────────────────────────────────────────────────
# Collection names (single source of truth)
# ──────────────────────────────────────────────────────────────────────────────
DEPARTMENTS_COLLECTION = "departments"
ACADEMIC_CONFIG_COLLECTION = "academic_config"


# ──────────────────────────────────────────────────────────────────────────────
# Department document
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class DepartmentDocument:
    """Represents one department stored in the 'departments' collection."""

    name: str                          # e.g. "MCA"
    code: str                          # e.g. "MCA" (short code, uppercase)
    total_semesters: int               # e.g. 4 for MCA, 8 for CSE
    active: bool = field(default=True)
    created_at: datetime = field(default_factory=datetime.utcnow)


def department_to_dict(dept: DepartmentDocument) -> dict:
    """Converts a DepartmentDocument to a MongoDB-ready dict."""
    return asdict(dept)


# ──────────────────────────────────────────────────────────────────────────────
# Academic config document
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class AcademicConfigDocument:
    """
    Stores institution-wide academic configuration as key-value pairs.
    A single document with key='sections' holds the list of valid sections.
    """

    key: str           # e.g. "sections"
    value: list        # e.g. ["A", "B", "C", "D"]
    updated_at: datetime = field(default_factory=datetime.utcnow)


def academic_config_to_dict(config: AcademicConfigDocument) -> dict:
    """Converts an AcademicConfigDocument to a MongoDB-ready dict."""
    return asdict(config)
