"""
app/services/timetable_service.py

Business logic for the Timetable Module.
"""
from typing import List, Dict
from datetime import datetime
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.models.timetable import TIMETABLE_COLLECTION, SUBJECT_COLLECTION
from app.models.student import STUDENT_COLLECTION

TEACHER_COLLECTION = "teachers"

async def _enrich_periods(periods: list, db: AsyncIOMotorDatabase) -> list:
    """Helper to fetch subject names and faculty names for the given periods."""
    enriched = []
    for p in periods:
        subject = await db[SUBJECT_COLLECTION].find_one({"subject_id": p.get("subject_id")})
        faculty = await db[TEACHER_COLLECTION].find_one({"_id": ObjectId(p.get("faculty_id"))}) if p.get("faculty_id") and len(p.get("faculty_id")) == 24 else None
        
        enriched_p = p.copy()
        enriched_p["subject_name"] = subject.get("subject_name") if subject else "Unknown Subject"
        enriched_p["subject_code"] = subject.get("subject_code") if subject else "---"
        enriched_p["faculty_name"] = faculty.get("full_name") or faculty.get("name") if faculty else "Unknown Faculty"
        enriched.append(enriched_p)
    return enriched

async def _seed_default_timetable_if_empty(dept: str, sem: int, sec: str, db: AsyncIOMotorDatabase):
    existing = await db[TIMETABLE_COLLECTION].find_one({
        "department": dept,
        "semester": sem,
        "section": sec
    })
    if existing:
        return

    schedule_data = {
        "Monday": [
            {"period_no": 1, "start_time": "09:00", "end_time": "10:00", "subject_id": "Data Structures", "room": "B-204", "is_cancelled": False},
            {"period_no": 2, "start_time": "10:15", "end_time": "11:15", "subject_id": "Operating Systems", "room": "C-101", "is_cancelled": False},
            {"period_no": 3, "start_time": "11:30", "end_time": "12:30", "subject_id": "Database Systems", "room": "A-312", "is_cancelled": False}
        ],
        "Tuesday": [
            {"period_no": 1, "start_time": "09:00", "end_time": "10:00", "subject_id": "Computer Networks", "room": "B-204", "is_cancelled": False},
            {"period_no": 2, "start_time": "10:15", "end_time": "11:15", "subject_id": "Software Engineering", "room": "Lab 1", "is_cancelled": False}
        ],
        "Wednesday": [
            {"period_no": 1, "start_time": "09:00", "end_time": "10:00", "subject_id": "Algorithms", "room": "C-101", "is_cancelled": False},
            {"period_no": 2, "start_time": "11:15", "end_time": "12:15", "subject_id": "Web Technologies", "room": "Lab 2", "is_cancelled": False}
        ],
        "Thursday": [
            {"period_no": 1, "start_time": "09:00", "end_time": "10:00", "subject_id": "Machine Learning", "room": "A-312", "is_cancelled": False},
            {"period_no": 2, "start_time": "10:15", "end_time": "11:15", "subject_id": "Cloud Computing", "room": "B-204", "is_cancelled": False}
        ],
        "Friday": [
            {"period_no": 1, "start_time": "09:00", "end_time": "10:00", "subject_id": "Cyber Security", "room": "C-101", "is_cancelled": False},
            {"period_no": 2, "start_time": "11:15", "end_time": "12:15", "subject_id": "Artificial Intelligence", "room": "Lab 1", "is_cancelled": False}
        ],
        "Saturday": [
            {"period_no": 1, "start_time": "09:00", "end_time": "12:00", "subject_id": "Seminar / Project Review", "room": "Auditorium", "is_cancelled": False}
        ]
    }

    for day, periods in schedule_data.items():
        doc = {
            "timetable_id": f"{dept}-{sem}-{sec}-{day}",
            "department": dept,
            "semester": sem,
            "section": sec,
            "day_of_week": day,
            "periods": periods,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db[TIMETABLE_COLLECTION].insert_one(doc)

async def get_student_timetable(student_id: str, db: AsyncIOMotorDatabase) -> list:
    student = await db[STUDENT_COLLECTION].find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    dept = student.get("department") or "CSE"
    sem = student.get("semester") or 5
    sec = student.get("section") or "A"

    await _seed_default_timetable_if_empty(dept, int(sem), str(sec), db)
        
    cursor = db[TIMETABLE_COLLECTION].find({
        "department": dept,
        "semester": int(sem),
        "section": str(sec),
        "is_active": True
    })
    
    timetables = await cursor.to_list(length=14)
    
    for t in timetables:
        t["periods"] = await _enrich_periods(t.get("periods", []), db)
        if "_id" in t:
            t["_id"] = str(t["_id"])
            
    return timetables

async def get_student_timetable_today(student_id: str, db: AsyncIOMotorDatabase) -> dict:
    student = await db[STUDENT_COLLECTION].find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    dept = student.get("department") or "CSE"
    sem = student.get("semester") or 5
    sec = student.get("section") or "A"

    await _seed_default_timetable_if_empty(dept, int(sem), str(sec), db)
        
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_str = days[datetime.today().weekday()]
    
    timetable = await db[TIMETABLE_COLLECTION].find_one({
        "department": dept,
        "semester": int(sem),
        "section": str(sec),
        "day_of_week": today_str,
        "is_active": True
    })
    
    if not timetable:
        return {"day_of_week": today_str, "periods": []}
        
    enriched_periods = await _enrich_periods(timetable.get("periods", []), db)
    enriched_periods.sort(key=lambda x: x.get("start_time", "00:00"))
    
    return {
        "day_of_week": today_str,
        "periods": enriched_periods
    }

async def get_student_subjects(student_id: str, db: AsyncIOMotorDatabase) -> list:
    student = await db[STUDENT_COLLECTION].find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    dept = student.get("department")
    sem = student.get("semester")
    
    if not dept or not sem:
        return []
        
    cursor = db[SUBJECT_COLLECTION].find({
        "department": dept,
        "semester": sem,
        "is_active": True
    })
    
    subjects = await cursor.to_list(length=50)
    for s in subjects:
        if "_id" in s:
            s["_id"] = str(s["_id"])
            
        faculty = await db[TEACHER_COLLECTION].find_one({"_id": ObjectId(s.get("faculty_id"))}) if s.get("faculty_id") and len(s.get("faculty_id")) == 24 else None
        s["faculty_name"] = faculty.get("full_name") or faculty.get("name") if faculty else "Unknown Faculty"
            
    return subjects

async def get_timetable_by_class(dept: str, sem: int, sec: str, db: AsyncIOMotorDatabase) -> list:
    cursor = db[TIMETABLE_COLLECTION].find({
        "department": dept,
        "semester": sem,
        "section": sec
    })
    timetables = await cursor.to_list(length=14)
    for t in timetables:
        if "_id" in t:
            t["_id"] = str(t["_id"])
        t["periods"] = await _enrich_periods(t.get("periods", []), db)
    return timetables

async def upsert_timetable_class(payload: dict, db: AsyncIOMotorDatabase) -> dict:
    dept = payload.get("department")
    sem = int(payload.get("semester"))
    sec = payload.get("section")
    day = payload.get("day_of_week")
    
    new_period = {
        "period_no": int(payload.get("period_no", 1)),
        "start_time": payload.get("start_time"),
        "end_time": payload.get("end_time"),
        "subject_id": payload.get("subject_id"),
        "faculty_id": payload.get("faculty_id", ""),
        "room": payload.get("room"),
        "is_cancelled": False
    }

    doc = await db[TIMETABLE_COLLECTION].find_one({
        "department": dept,
        "semester": sem,
        "section": sec,
        "day_of_week": day
    })

    if doc:
        periods = doc.get("periods", [])
        periods = [p for p in periods if p.get("period_no") != new_period["period_no"]]
        periods.append(new_period)
        periods.sort(key=lambda x: x.get("period_no", 1))
        await db[TIMETABLE_COLLECTION].update_one(
            {"_id": doc["_id"]},
            {"$set": {"periods": periods, "updated_at": datetime.utcnow()}}
        )
    else:
        new_doc = {
            "timetable_id": f"{dept}-{sem}-{sec}-{day}",
            "department": dept,
            "semester": sem,
            "section": sec,
            "day_of_week": day,
            "periods": [new_period],
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db[TIMETABLE_COLLECTION].insert_one(new_doc)

    return {"success": True, "message": "Class period saved to timetable successfully."}
