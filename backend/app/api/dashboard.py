"""数据看板接口（M4）"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.response import ok
from app.models import (
    AttendanceRecord,
    Course,
    DormCheck,
    ScoreRecord,
    StudentProfile,
    SysUser,
)

router = APIRouter(prefix="/dashboard", tags=["看板"])


def _latest_semester(db: Session) -> str:
    latest = db.query(Course).order_by(Course.semester.desc()).first()
    return latest.semester if latest else ""


@router.get("/overview")
def overview(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = user.class_id
    total_students = db.query(StudentProfile).filter(
        StudentProfile.class_id == cid, StudentProfile.deleted_at.is_(None)
    ).count()

    # 今日出勤率
    today = date.today()
    today_records = db.query(AttendanceRecord).filter(
        AttendanceRecord.class_id == cid, AttendanceRecord.att_date == today
    ).all()
    today_rate = None
    if today_records:
        denominator = [r for r in today_records if r.status not in ("LEAVE_APPROVED", "PUBLIC_LEAVE")]
        present = [r for r in denominator if r.status in ("NORMAL", "LATE", "EARLY_LEAVE")]
        today_rate = round(len(present) / len(denominator), 4) if denominator else 1.0

    # 本周旷课人次
    week_start = today - timedelta(days=today.weekday())
    week_absent = db.query(AttendanceRecord).filter(
        AttendanceRecord.class_id == cid,
        AttendanceRecord.status == "ABSENT",
        AttendanceRecord.att_date >= week_start,
    ).count()

    # 当前学期挂科人数
    semester = _latest_semester(db)
    fail_students = 0
    if semester:
        scores = db.query(ScoreRecord).filter(ScoreRecord.semester == semester).all()
        by_student: dict[int, list] = {}
        for sc in scores:
            by_student.setdefault(sc.student_id, []).append(sc.score)
        fail_students = sum(
            1 for vals in by_student.values() if any(v is not None and v < 60 for v in vals)
        )

    return ok(
        {
            "total_students": total_students,
            "today_rate": today_rate,
            "week_absent": week_absent,
            "fail_students": fail_students,
            "semester": semester,
        }
    )


@router.get("/attendance-trend")
def attendance_trend(
    days: int = 30,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = user.class_id
    start = date.today() - timedelta(days=days - 1)
    records = db.query(AttendanceRecord).filter(
        AttendanceRecord.class_id == cid, AttendanceRecord.att_date >= start
    ).all()
    by_date: dict[str, list] = {}
    for r in records:
        by_date.setdefault(r.att_date.isoformat(), []).append(r)
    result = []
    for i in range(days):
        d = start + timedelta(days=i)
        key = d.isoformat()
        rs = by_date.get(key, [])
        denominator = [r for r in rs if r.status not in ("LEAVE_APPROVED", "PUBLIC_LEAVE")]
        present = [r for r in denominator if r.status in ("NORMAL", "LATE", "EARLY_LEAVE")]
        rate = round(len(present) / len(denominator) * 100, 2) if denominator else None
        result.append({"date": key, "rate": rate})
    return ok(result)


@router.get("/score-distribution")
def score_distribution(
    semester: str | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sem = semester or _latest_semester(db)
    scores = db.query(ScoreRecord).filter(ScoreRecord.semester == sem).all()
    buckets = {"lt60": 0, "60_74": 0, "75_84": 0, "85_100": 0}
    for sc in scores:
        if sc.score is None:
            continue
        if sc.score < 60:
            buckets["lt60"] += 1
        elif sc.score < 75:
            buckets["60_74"] += 1
        elif sc.score < 85:
            buckets["75_84"] += 1
        else:
            buckets["85_100"] += 1
    return ok(
        [
            {"name": "<60", "value": buckets["lt60"]},
            {"name": "60-74", "value": buckets["60_74"]},
            {"name": "75-84", "value": buckets["75_84"]},
            {"name": "85-100", "value": buckets["85_100"]},
        ]
    )


@router.get("/rankings")
def rankings(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    # 旷课 Top
    absent = (
        db.query(AttendanceRecord.student_id, func.count().label("cnt"))
        .filter(AttendanceRecord.status == "ABSENT")
        .group_by(AttendanceRecord.student_id)
        .order_by(func.count().desc())
        .limit(10)
        .all()
    )
    # 晚归/未归 Top
    dorm = (
        db.query(DormCheck.student_id, func.count().label("cnt"))
        .filter(DormCheck.status.in_(["LATE_BACK", "NOT_IN"]))
        .group_by(DormCheck.student_id)
        .order_by(func.count().desc())
        .limit(10)
        .all()
    )

    def _name(sid):
        s = db.get(StudentProfile, sid)
        return s.name if s else ""

    return ok(
        {
            "absent_top": [{"student_id": x[0], "name": _name(x[0]), "count": x[1]} for x in absent],
            "dorm_top": [{"student_id": x[0], "name": _name(x[0]), "count": x[1]} for x in dorm],
        }
    )
