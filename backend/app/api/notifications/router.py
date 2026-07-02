"""
app/api/notifications/router.py

Notifications module router.
Endpoints will be implemented in a future sprint.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/ping")
async def ping():
    """Temporary health check — confirms the notifications module is registered."""
    return {"module": "notifications", "status": "ready"}
