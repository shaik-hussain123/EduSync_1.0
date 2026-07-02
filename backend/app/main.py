"""
app/main.py

FastAPI application entry point for EduSync ERP.
Responsibilities:
  - Configure logging
  - Manage application lifespan (DB connect / disconnect)
  - Register CORS middleware
  - Mount the versioned API router (/api/v1)
  - Expose top-level utility endpoints (/ and /health)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, db_manager, get_database
from app.core.security import hash_password
from app.services.academic_service import seed_academic_data

# ── Module routers ────────────────────────────────────────────────────────────
from app.api.auth.router import router as auth_router
from app.api.student.router import router as student_router
from app.api.teacher.router import router as teacher_router
from app.api.admin.router import router as admin_router
from app.api.attendance.router import router as attendance_router
from app.api.face.router import router as face_router
from app.api.notifications.router import router as notifications_router
from app.api.settings.router import router as settings_router

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def seed_demo_accounts(db):
    """Ensure a small set of local demo accounts exists for browser verification."""
    student_collection = db["students"]
    teacher_collection = db["teachers"]

    student_exists = await student_collection.find_one({"email": "student@example.com"})
    if not student_exists:
        await student_collection.insert_one({
            "full_name": "Ada Lovelace",
            "email": "student@example.com",
            "password": hash_password("password"),
            "usn": "1AB22CS001",
            "department": "CSE",
            "semester": 5,
            "section": "A",
            "phone": "9876543210",
            "gender": "Female",
            "date_of_birth": "2003-10-15",
            "profile_photo": None,
            "role": "student",
            "verification_status": "approved",
            "face_registered": False,
            "profile_completed": True,
            "account_status": "active",
            "created_at": __import__("datetime").datetime.utcnow(),
            "updated_at": __import__("datetime").datetime.utcnow(),
        })
        logger.info("Seeded demo student account")

    teacher_exists = await teacher_collection.find_one({"email": "teacher@example.com"})
    if not teacher_exists:
        await teacher_collection.insert_one({
            "full_name": "Dr. John Smith",
            "email": "teacher@example.com",
            "password_hash": hash_password("password"),
            "department": "CSE",
            "role": "teacher",
            "is_active": True,
            "account_status": "active",
            "created_at": __import__("datetime").datetime.utcnow(),
            "updated_at": __import__("datetime").datetime.utcnow(),
        })
        logger.info("Seeded demo teacher account")

    admin_collection = db["admins"]
    admin_exists = await admin_collection.find_one({"email": "admin@example.com"})
    if not admin_exists:
        await admin_collection.insert_one({
            "full_name": "System Administrator",
            "email": "admin@example.com",
            "password_hash": hash_password("password"),
            "role": "admin",
            "is_active": True,
            "account_status": "active",
            "created_at": __import__("datetime").datetime.utcnow(),
            "updated_at": __import__("datetime").datetime.utcnow(),
        })
        logger.info("Seeded demo admin account")



# ──────────────────────────────────────────────────────────────────────────────
# CORS — Origins allowed during development
# Add production origins here (or load from settings) before deploying.
# ──────────────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS: list[str] = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


# ──────────────────────────────────────────────────────────────────────────────
# Lifespan — startup & graceful shutdown
# ──────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern FastAPI lifespan handler.
    - Startup : Establish MongoDB connection.
    - Shutdown: Close MongoDB connection gracefully.
    """
    logger.info(f"Starting up {settings.PROJECT_NAME} ...")
    try:
        await connect_to_mongo()
        # Seed departments and academic config (idempotent — safe on every restart)
        db = get_database()
        await seed_academic_data(db)
        await seed_demo_accounts(db)
    except Exception:
        logger.warning(
            "Application started with database connection failure. "
            "The /health endpoint will report 'unhealthy'."
        )

    yield  # ← application is live; requests are handled here

    logger.info(f"Shutting down {settings.PROJECT_NAME} ...")
    await close_mongo_connection()
    logger.info("Shutdown complete.")


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI Instance
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description="Backend API for EduSync — Smart Campus ERP, an intelligent educational management system.",
    lifespan=lifespan,
)


# ──────────────────────────────────────────────────────────────────────────────
# Middleware
# ──────────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# API v1 — versioned router group
# All module routers live under /api/v1
# ──────────────────────────────────────────────────────────────────────────────
API_V1_PREFIX = "/api/v1"

for module_router in [
    auth_router,
    student_router,
    teacher_router,
    admin_router,
    attendance_router,
    face_router,
    notifications_router,
    settings_router,
]:
    app.include_router(module_router, prefix=API_V1_PREFIX)


# ──────────────────────────────────────────────────────────────────────────────
# Top-level Utility Endpoints
# These remain outside the /api/v1 prefix intentionally.
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint — confirms the API is running."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": settings.API_VERSION,
    }


@app.post("/login", tags=["Root"])
async def root_login(payload: dict):
    from fastapi import HTTPException
    from app.api.auth.router import unified_login, UnifiedLoginRequest
    role = payload.get("role")
    email = payload.get("email")
    password = payload.get("password")
    if not role or not email or not password:
        raise HTTPException(status_code=400, detail="Missing role, email, or password")
    
    try:
        req = UnifiedLoginRequest(role=role, email=email, password=password)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return await unified_login(req)



@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    - HTTP 200 + 'healthy'    → MongoDB is reachable.
    - HTTP 503 + 'unhealthy'  → MongoDB is disconnected.
    """
    if db_manager.client is not None:
        try:
            await db_manager.client.admin.command("ping")
            return {
                "status": "healthy",
                "database": "connected",
                "project": settings.PROJECT_NAME,
            }
        except Exception as e:
            logger.error(f"Health check: MongoDB ping failed — {e}")

    return JSONResponse(
        status_code=503,
        content={"status": "unhealthy", "database": "disconnected"},
    )
