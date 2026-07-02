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

async def get_student_timetable(student_id: str, db: AsyncIOMotorDatabase) -> list:
    student = await db[STUDENT_COLLECTION].find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    dept = student.get("department")
    sem = student.get("semester")
    sec = student.get("section")
    
    if not dept or not sem or not sec:
        return []
        
    cursor = db[TIMETABLE_COLLECTION].find({
        "department": dept,
        "semester": sem,
        "section": sec,
        "is_active": True
    })
    
    timetables = await cursor.to_list(length=10)
    
    # Enrich all periods
    for t in timetables:
        t["periods"] = await _enrich_periods(t.get("periods", []), db)
        # Convert _id to string for JSON serialization
        if "_id" in t:
            t["_id"] = str(t["_id"])
            
    return timetables

async def get_student_timetable_today(student_id: str, db: AsyncIOMotorDatabase) -> dict:
    student = await db[STUDENT_COLLECTION].find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    dept = student.get("department")
    sem = student.get("semester")
    sec = student.get("section")
    
    if not dept or not sem or not sec:
        return {"periods": []}
        
    # Get current day of week as string (e.g. "Monday")
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_str = days[datetime.today().weekday()]
    
    timetable = await db[TIMETABLE_COLLECTION].find_one({
        "department": dept,
        "semester": sem,
        "section": sec,
        "day_of_week": today_str,
        "is_active": True
    })
    
    if not timetable:
        return {"day_of_week": today_str, "periods": []}
        
    enriched_periods = await _enrich_periods(timetable.get("periods", []), db)
    
    # Sort periods by start time
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
