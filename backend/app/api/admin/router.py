"""
app/api/admin/router.py

Admin module router with management endpoints.
"""
import logging
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.database import get_database
from app.core.security import verify_password, hash_password, create_access_token
from app.auth_dependencies import get_current_admin
from app.models.student import STUDENT_COLLECTION
from app.models.academic import DEPARTMENTS_COLLECTION
from app.models.timetable import SUBJECT_COLLECTION, TIMETABLE_COLLECTION
from app.models.audit import AUDIT_LOG_COLLECTION, AuditLogDocument, audit_log_to_dict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

# ── Request/Response Schemas ──────────────────────────────────────────────────
class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str

class AdminLoginResponse(BaseModel):
    success: bool
    message: str
    access_token: str
    token_type: str
    admin: dict

class TeacherCreateRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    department: str
    employee_id: str
    designation: Optional[str] = "Assistant Professor"
    subjects: List[str] = []

class DepartmentCreateRequest(BaseModel):
    name: str
    code: str
    total_semesters: int = 8

class SubjectCreateRequest(BaseModel):
    subject_id: str
    subject_code: str
    subject_name: str
    department: str
    semester: int
    credits: int
    faculty_id: str

class StudentVerifyRequest(BaseModel):
    status: str  # approved, rejected

class StudentStatusRequest(BaseModel):
    status: str  # active, blocked

class TeacherStatusRequest(BaseModel):
    is_active: bool

# ── Helper functions ──────────────────────────────────────────────────────────
async def log_audit(action: str, actor: str, target: str, details: str, db: AsyncIOMotorDatabase) -> None:
    try:
        doc = AuditLogDocument(action=action, actor=actor, target=target, details=details)
        await db[AUDIT_LOG_COLLECTION].insert_one(audit_log_to_dict(doc))
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/ping")
async def ping():
    """Temporary health check — confirms the admin module is registered."""
    return {"module": "admin", "status": "ready"}

@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(payload: AdminLoginRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Authenticate administrator and return access token."""
    admin = await db["admins"].find_one({"email": payload.email})
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
        
    if not verify_password(payload.password, admin.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if admin.get("account_status", "active") != "active" or not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="Admin account is inactive.")

    token_payload = {
        "admin_id": str(admin["_id"]),
        "email": admin["email"],
        "role": "admin"
    }
    token = create_access_token(token_payload)
    
    await log_audit("admin_login", admin["email"], admin["email"], "Administrator logged in successfully.", db)

    return AdminLoginResponse(
        success=True,
        message="Login successful.",
        access_token=token,
        token_type="bearer",
        admin={
            "id": str(admin["_id"]),
            "full_name": admin.get("full_name", "Admin"),
            "email": admin["email"],
            "role": "admin"
        }
    )

@router.get("/stats")
async def get_stats(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Fetch dashboard counts and configurations."""
    total_students = await db[STUDENT_COLLECTION].count_documents({})
    pending_students = await db[STUDENT_COLLECTION].count_documents({"verification_status": "pending"})
    approved_students = await db[STUDENT_COLLECTION].count_documents({"verification_status": "approved"})
    
    total_teachers = await db["teachers"].count_documents({})
    total_departments = await db[DEPARTMENTS_COLLECTION].count_documents({"active": True})
    
    return {
        "students": {
            "total": total_students,
            "pending": pending_students,
            "approved": approved_students
        },
        "teachers": {
            "total": total_teachers
        },
        "departments": {
            "total": total_departments
        }
    }

# ── Student Management ────────────────────────────────────────────────────────

@router.get("/students")
async def list_students(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List all registered student accounts."""
    cursor = db[STUDENT_COLLECTION].find({})
    students = await cursor.to_list(length=1000)
    for s in students:
        s["id"] = str(s["_id"])
        del s["_id"]
        if "password" in s:
            del s["password"]
    return {"students": students}

@router.put("/students/{student_id}/verify")
async def verify_student(
    student_id: str,
    payload: StudentVerifyRequest,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Approve or reject a pending student registration."""
    if payload.status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid verification status.")
        
    res = await db[STUDENT_COLLECTION].find_one({"_id": ObjectId(student_id)})
    if not res:
        raise HTTPException(status_code=404, detail="Student not found.")
        
    await db[STUDENT_COLLECTION].update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"verification_status": payload.status, "updated_at": datetime.utcnow()}}
    )
    
    await log_audit(
        f"student_{payload.status}", 
        current_admin["email"], 
        res["email"], 
        f"Student registration {payload.status} by administrator.", 
        db
    )
    return {"success": True, "message": f"Student registration status updated to: {payload.status}."}

@router.put("/students/{student_id}/status")
async def update_student_status(
    student_id: str,
    payload: StudentStatusRequest,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Block or unblock a student account."""
    if payload.status not in ["active", "blocked"]:
        raise HTTPException(status_code=400, detail="Invalid account status.")
        
    res = await db[STUDENT_COLLECTION].find_one({"_id": ObjectId(student_id)})
    if not res:
        raise HTTPException(status_code=404, detail="Student not found.")
        
    await db[STUDENT_COLLECTION].update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"account_status": payload.status, "updated_at": datetime.utcnow()}}
    )
    
    await log_audit(
        f"student_{payload.status}", 
        current_admin["email"], 
        res["email"], 
        f"Student account status updated to {payload.status}.", 
        db
    )
    return {"success": True, "message": f"Student account status updated to {payload.status}."}

@router.delete("/students/{student_id}")
async def delete_student(
    student_id: str,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete a student account."""
    res = await db[STUDENT_COLLECTION].find_one({"_id": ObjectId(student_id)})
    if not res:
        raise HTTPException(status_code=404, detail="Student not found.")
        
    await db[STUDENT_COLLECTION].delete_one({"_id": ObjectId(student_id)})
    await log_audit("student_deleted", current_admin["email"], res["email"], "Student deleted from ERP.", db)
    return {"success": True, "message": "Student deleted successfully."}

# ── Teacher Management ────────────────────────────────────────────────────────

@router.get("/teachers")
async def list_teachers(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List all teacher accounts."""
    cursor = db["teachers"].find({})
    teachers = await cursor.to_list(length=500)
    for t in teachers:
        t["id"] = str(t["_id"])
        del t["_id"]
        if "password_hash" in t:
            del t["password_hash"]
    return {"teachers": teachers}

@router.post("/teachers", status_code=status.HTTP_201_CREATED)
async def create_teacher(
    payload: TeacherCreateRequest,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Register a new teacher account."""
    existing = await db["teachers"].find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered to another teacher.")

    teacher_doc = {
        "full_name": payload.full_name,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "department": payload.department,
        "employee_id": payload.employee_id,
        "designation": payload.designation,
        "subjects": payload.subjects,
        "role": "teacher",
        "is_active": True,
        "account_status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    await db["teachers"].insert_one(teacher_doc)
    await log_audit("teacher_created", current_admin["email"], payload.email, f"New teacher account created for {payload.full_name}.", db)
    return {"success": True, "message": "Teacher account created successfully."}

@router.put("/teachers/{teacher_id}/status")
async def update_teacher_status(
    teacher_id: str,
    payload: TeacherStatusRequest,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Enable or disable a teacher account."""
    res = await db["teachers"].find_one({"_id": ObjectId(teacher_id)})
    if not res:
        raise HTTPException(status_code=404, detail="Teacher not found.")
        
    status_str = "active" if payload.is_active else "inactive"
    await db["teachers"].update_one(
        {"_id": ObjectId(teacher_id)},
        {"$set": {"is_active": payload.is_active, "account_status": status_str, "updated_at": datetime.utcnow()}}
    )
    
    await log_audit(
        f"teacher_{status_str}", 
        current_admin["email"], 
        res["email"], 
        f"Teacher account status set to {status_str}.", 
        db
    )
    return {"success": True, "message": f"Teacher account status set to {status_str}."}

@router.delete("/teachers/{teacher_id}")
async def delete_teacher(
    teacher_id: str,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete a teacher account."""
    res = await db["teachers"].find_one({"_id": ObjectId(teacher_id)})
    if not res:
        raise HTTPException(status_code=404, detail="Teacher not found.")
        
    await db["teachers"].delete_one({"_id": ObjectId(teacher_id)})
    await log_audit("teacher_deleted", current_admin["email"], res["email"], "Teacher deleted from ERP.", db)
    return {"success": True, "message": "Teacher deleted successfully."}

# ── Department Management ─────────────────────────────────────────────────────

@router.get("/departments")
async def list_departments(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List all departments."""
    cursor = db[DEPARTMENTS_COLLECTION].find({})
    depts = await cursor.to_list(length=100)
    for d in depts:
        d["id"] = str(d["_id"])
        del d["_id"]
    return {"departments": depts}

@router.post("/departments", status_code=status.HTTP_201_CREATED)
async def create_department(
    payload: DepartmentCreateRequest,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new department."""
    existing = await db[DEPARTMENTS_COLLECTION].find_one({"code": payload.code.upper()})
    if existing:
        raise HTTPException(status_code=409, detail="Department with this code already exists.")
        
    dept_doc = {
        "name": payload.name,
        "code": payload.code.upper(),
        "total_semesters": payload.total_semesters,
        "active": True,
        "created_at": datetime.utcnow()
    }
    await db[DEPARTMENTS_COLLECTION].insert_one(dept_doc)
    await log_audit("department_created", current_admin["email"], payload.code.upper(), f"Department '{payload.name}' created.", db)
    return {"success": True, "message": "Department created successfully."}

@router.put("/departments/{code}/status")
async def update_department_status(
    code: str,
    payload: dict,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Toggle department active status."""
    is_active = payload.get("active", True)
    res = await db[DEPARTMENTS_COLLECTION].find_one({"code": code.upper()})
    if not res:
        raise HTTPException(status_code=404, detail="Department not found.")
        
    await db[DEPARTMENTS_COLLECTION].update_one(
        {"code": code.upper()},
        {"$set": {"active": is_active}}
    )
    status_str = "activated" if is_active else "deactivated"
    await log_audit("department_status", current_admin["email"], code.upper(), f"Department {status_str}.", db)
    return {"success": True, "message": f"Department {status_str}."}

# ── Subject Management ────────────────────────────────────────────────────────

@router.get("/subjects")
async def list_subjects(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List all subjects."""
    cursor = db[SUBJECT_COLLECTION].find({})
    subjects = await cursor.to_list(length=1000)
    for s in subjects:
        s["id"] = str(s["_id"])
        del s["_id"]
        
        # Enrich with faculty name
        if s.get("faculty_id") and len(s["faculty_id"]) == 24:
            f = await db["teachers"].find_one({"_id": ObjectId(s["faculty_id"])})
            s["faculty_name"] = f.get("full_name", "Teacher") if f else "Unknown Faculty"
        else:
            s["faculty_name"] = "Not Assigned"
            
    return {"subjects": subjects}

@router.post("/subjects", status_code=status.HTTP_201_CREATED)
async def create_subject(
    payload: SubjectCreateRequest,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new subject and assign a faculty member."""
    existing = await db[SUBJECT_COLLECTION].find_one({"subject_code": payload.subject_code.upper()})
    if existing:
        raise HTTPException(status_code=409, detail="Subject with this code already exists.")
        
    sub_doc = {
        "subject_id": payload.subject_id,
        "subject_code": payload.subject_code.upper(),
        "subject_name": payload.subject_name,
        "department": payload.department,
        "semester": payload.semester,
        "credits": payload.credits,
        "faculty_id": payload.faculty_id,
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    await db[SUBJECT_COLLECTION].insert_one(sub_doc)
    await log_audit("subject_created", current_admin["email"], payload.subject_code.upper(), f"Subject '{payload.subject_name}' created.", db)
    return {"success": True, "message": "Subject created successfully."}

# ── Audit Logs ────────────────────────────────────────────────────────────────

@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 50,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Fetch system audit logs sorted by newest first."""
    cursor = db[AUDIT_LOG_COLLECTION].find().sort("timestamp", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    formatted_logs = []
    for l in logs:
        ts = l.get("timestamp")
        if isinstance(ts, datetime):
            ts = ts.strftime("%Y-%m-%d %H:%M:%S")
        formatted_logs.append({
            "id": str(l.get("_id", "")),
            "action": str(l.get("action", "")),
            "actor": str(l.get("actor", "")),
            "target": str(l.get("target", "")),
            "details": str(l.get("details", "")),
            "timestamp": str(ts or "")
        })
    return {"success": True, "logs": formatted_logs}

@router.post("/timetable/upsert")
async def admin_upsert_timetable(
    payload: dict,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create or update a class period in the timetable."""
    from app.services.timetable_service import upsert_timetable_class
    res = await upsert_timetable_class(payload, db)
    await log_audit("timetable_update", current_admin["email"], payload.get("department", "general"), f"Updated timetable for {payload.get('department')} Sem {payload.get('semester')} Sec {payload.get('section')}.", db)
    return res

@router.get("/timetable")
async def admin_get_timetable(
    department: str,
    semester: int,
    section: str,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Fetch class timetable by department, semester, and section."""
    from app.services.timetable_service import get_timetable_by_class
    timetables = await get_timetable_by_class(department, semester, section, db)
    return {"success": True, "timetables": timetables}
