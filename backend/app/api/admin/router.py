"""
app/api/admin/router.py

Admin module router.
Endpoints will be implemented in Sprint 2.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/ping")
async def ping():
    """Temporary health check — confirms the admin module is registered."""
    return {"module": "admin", "status": "ready"}
