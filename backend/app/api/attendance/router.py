"""
app/api/attendance/router.py

Attendance module router.
Endpoints will be implemented in a future sprint.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("/ping")
async def ping():
    """Temporary health check — confirms the attendance module is registered."""
    return {"module": "attendance", "status": "ready"}
