"""考勤接口（M2）"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, write_audit
from app.core.response import BizError, ok
from app.models import AttendanceRecord, StudentProfile, SysUser
from app.schemas import AttendanceBatchRequest
from app.utils import export_rows_to_xlsx

router = APIRouter(prefix="/attendance", tags=["考勤"])

SESSIONS = ["MORNING_SELF", "AM", "PM", "EVENING_SELF", "DAILY_EXERCISE"]
SESSION_LABEL = {
    "MORNING_SELF": "早自习",
    "AM": "上午课程",
    "PM": "下午课程",
    "EVENING_SELF": "晚自修",
    "DAILY_EXERCISE": "出操",
}
STATUS_LABEL = {
    "NORMAL": "出勤",
    "LATE": "迟到",
    "EARLY_LEAVE": "早退",
    "ABSENT": "旷课",
    "LEAVE_APPROVED": "请假",
    "PUBLIC_LEAVE": "公假",
}


@router.post("/batch")
def batch_attendance(
    body: AttendanceBatchRequest,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.session not in SESSIONS:
        raise BizError("无效的节次", 400)
    cid = body.class_id or user.class_id
    if cid is None:
        from app.models import ClassInfo
        cls = db.query(ClassInfo).first()
        if cls is None:
            raise BizError("请先创建班级", 400)
        cid = cls.id
    students = (
        db.query(StudentProfile)
        .filter(StudentProfile.class_id == cid, StudentProfile.deleted_at.is_(None))
        .all()
    )
    for s in students:
        status = body.records.get(s.id, "NORMAL")
        if status not in STATUS_LABEL:
            raise BizError(f"无效的考勤状态: {status}", 400)
        existing = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.student_id == s.id,
                AttendanceRecord.att_date == body.att_date,
                AttendanceRecord.session == body.session,
            )
            .first()
        )
        if existing:
            existing.status = status
            existing.remark = body.remark
        else:
            db.add(
                AttendanceRecord(
                    student_id=s.id,
                    class_id=cid,
                    att_date=body.att_date,
                    session=body.session,
                    status=status,
                    remark=body.remark,
                    recorder_id=user.id,
                )
            )
    write_audit(db, "CREATE", "attendance_record", None, f"考勤 {body.att_date} {SESSION_LABEL.get(body.session)}", user.id, request.client.host if request.client else None)
    db.commit()
    return ok(None, message="考勤已保存")


@router.get("")
def list_attendance(
    att_date: date | None = None,
    session: str | None = None,
    class_id: int | None = None,
    student_id: int | None = None,
    page: int = 1,
    size: int = 50,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(AttendanceRecord)
    if att_date:
        q = q.filter(AttendanceRecord.att_date == att_date)
    if session:
        q = q.filter(AttendanceRecord.session == session)
    if class_id:
        q = q.filter(AttendanceRecord.class_id == class_id)
    if student_id:
        q = q.filter(AttendanceRecord.student_id == student_id)
    total = q.count()
    items = q.order_by(AttendanceRecord.att_date.desc()).offset((page - 1) * size).limit(size).all()
    data = []
    for r in items:
        s = db.get(StudentProfile, r.student_id)
        data.append(
            {
                "id": r.id,
                "student_id": r.student_id,
                "student_name": s.name if s else "",
                "student_no": s.student_no if s else "",
                "att_date": r.att_date.isoformat() if r.att_date else None,
                "session": r.session,
                "session_label": SESSION_LABEL.get(r.session, r.session),
                "status": r.status,
                "status_label": STATUS_LABEL.get(r.status, r.status),
                "remark": r.remark,
            }
        )
    return ok(data, total=total)


@router.get("/summary")
def attendance_summary(
    class_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = class_id or user.class_id
    students = (
        db.query(StudentProfile)
        .filter(StudentProfile.class_id == cid, StudentProfile.deleted_at.is_(None))
        .all()
    )
    q = db.query(AttendanceRecord).filter(AttendanceRecord.class_id == cid)
    if start_date:
        q = q.filter(AttendanceRecord.att_date >= start_date)
    if end_date:
        q = q.filter(AttendanceRecord.att_date <= end_date)
    records = q.all()
    # 按学生聚合
    stat = {s.id: {"normal": 0, "late": 0, "early_leave": 0, "absent": 0, "leave": 0, "public": 0, "total": 0} for s in students}
    for r in records:
        if r.student_id not in stat:
            continue
        stat[r.student_id]["total"] += 1
        key = {
            "NORMAL": "normal",
            "LATE": "late",
            "EARLY_LEAVE": "early_leave",
            "ABSENT": "absent",
            "LEAVE_APPROVED": "leave",
            "PUBLIC_LEAVE": "public",
        }.get(r.status, "normal")
        stat[r.student_id][key] += 1
    data = []
    for s in students:
        st = stat[s.id]
        # 出勤率：应出勤 = total - leave - public；出勤 = normal + late + early_leave
        denominator = st["total"] - st["leave"] - st["public"]
        rate = (st["normal"] + st["late"] + st["early_leave"]) / denominator if denominator > 0 else 1.0
        data.append(
            {
                "student_id": s.id,
                "student_name": s.name,
                "student_no": s.student_no,
                "normal": st["normal"],
                "late": st["late"],
                "early_leave": st["early_leave"],
                "absent": st["absent"],
                "leave": st["leave"],
                "public": st["public"],
                "attendance_rate": round(rate, 4),
            }
        )
    return ok(data)


@router.get("/export")
def export_attendance(
    class_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = class_id or user.class_id
    q = db.query(AttendanceRecord).filter(AttendanceRecord.class_id == cid)
    if start_date:
        q = q.filter(AttendanceRecord.att_date >= start_date)
    if end_date:
        q = q.filter(AttendanceRecord.att_date <= end_date)
    records = q.order_by(AttendanceRecord.att_date).all()
    headers = ["日期", "节次", "学号", "姓名", "状态", "备注"]
    rows = []
    for r in records:
        s = db.get(StudentProfile, r.student_id)
        rows.append(
            [
                r.att_date.isoformat() if r.att_date else "",
                SESSION_LABEL.get(r.session, r.session),
                s.student_no if s else "",
                s.name if s else "",
                STATUS_LABEL.get(r.status, r.status),
                r.remark or "",
            ]
        )
    content = export_rows_to_xlsx(headers, rows, "考勤台账")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=attendance.xlsx"},
    )
