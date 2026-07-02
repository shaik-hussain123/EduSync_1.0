"""Compatibility exports for authentication dependencies."""

from app.auth_dependencies import get_current_student, get_current_teacher, get_current_admin

__all__ = ["get_current_student", "get_current_teacher", "get_current_admin"]

