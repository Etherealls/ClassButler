"""学业预警、补考重修、荣誉（竞赛/证书）接口（M3）"""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, write_audit
from app.core.response import BizError, ok
from app.models import (
    AttendanceRecord,
    Certificate,
    CompetitionAward,
    Course,
    MakeupTrack,
    ScoreRecord,
    StudentProfile,
    SysUser,
)
from app.schemas import (
    AwardCreate,
    CertificateCreate,
    MakeupCreate,
    MakeupUpdate,
)
from app.utils import export_rows_to_xlsx

router = APIRouter(tags=["预警与荣誉"])


# ---------- 学业预警 ----------
@router.get("/alerts")
def list_alerts(
    semester: str | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """学业预警名单（含原因标签）"""
    students = (
        db.query(StudentProfile)
        .filter(StudentProfile.deleted_at.is_(None))
        .order_by(StudentProfile.student_no)
        .all()
    )
    # 当前学期默认取最新学期
    if semester is None:
        latest = db.query(Course).order_by(Course.semester.desc()).first()
        semester = latest.semester if latest else ""
    courses = db.query(Course).filter(Course.semester == semester).all()
    course_ids = [c.id for c in courses]

    result = []
    for s in students:
        scores = db.query(ScoreRecord).filter(
            ScoreRecord.student_id == s.id, ScoreRecord.semester == semester
        ).all()
        valid = [sc.score for sc in scores if sc.score is not None]
        fail_count = sum(1 for v in valid if v < 60)
        avg = sum(valid) / len(valid) if valid else None

        # 上一学期均分
        semesters = sorted(
            {c.semester for c in db.query(Course).all() if c.semester < semester}
        )
        prev_avg = None
        if semesters:
            prev_sem = semesters[-1]
            prev_scores = db.query(ScoreRecord).filter(
                ScoreRecord.student_id == s.id, ScoreRecord.semester == prev_sem
            ).all()
            prev_valid = [sc.score for sc in prev_scores if sc.score is not None]
            if prev_valid:
                prev_avg = sum(prev_valid) / len(prev_valid)

        # 旷课节次
        absent_count = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.student_id == s.id,
                AttendanceRecord.status == "ABSENT",
            )
            .count()
        )

        tags = []
        if fail_count >= 3:
            tags.append("重点预警")
        elif fail_count >= 1:
            tags.append("挂科")
        if prev_avg is not None and avg is not None and (avg - prev_avg) <= -15:
            tags.append("滑坡")
        if absent_count >= 5:
            tags.append("出勤预警")

        result.append(
            {
                "student_id": s.id,
                "student_name": s.name,
                "student_no": s.student_no,
                "semester": semester,
                "fail_count": fail_count,
                "average": round(avg, 2) if avg is not None else None,
                "prev_average": round(prev_avg, 2) if prev_avg is not None else None,
                "absent_count": absent_count,
                "tags": tags,
                "level": "high" if "重点预警" in tags else ("mid" if tags else "none"),
            }
        )

    return ok(result)


@router.get("/alerts/export")
def export_alerts(
    semester: str | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alerts = list_alerts(semester=semester, user=user, db=db)["data"]
    headers = ["学号", "姓名", "学期", "挂科门数", "平均分", "上学期均分", "旷课节次", "预警标签"]
    rows = [
        [
            a["student_no"], a["student_name"], a["semester"], a["fail_count"],
            a["average"], a["prev_average"], a["absent_count"], "、".join(a["tags"]),
        ]
        for a in alerts
        if a["tags"]
    ]
    content = export_rows_to_xlsx(headers, rows, "预警名单")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=alerts.xlsx"},
    )


# ---------- 补考重修 ----------
@router.get("/makeup")
def list_makeup(
    student_id: int | None = None,
    stage: str | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(MakeupTrack)
    if student_id:
        q = q.filter(MakeupTrack.student_id == student_id)
    if stage:
        q = q.filter(MakeupTrack.stage == stage)
    items = q.order_by(MakeupTrack.id.desc()).all()
    data = []
    for m in items:
        s = db.get(StudentProfile, m.student_id)
        c = db.get(Course, m.course_id)
        data.append(
            {
                "id": m.id,
                "student_id": m.student_id,
                "student_name": s.name if s else "",
                "student_no": s.student_no if s else "",
                "course_id": m.course_id,
                "course_name": c.course_name if c else "",
                "stage": m.stage,
                "exam_time": m.exam_time.strftime("%Y-%m-%d %H:%M") if m.exam_time else None,
                "result_score": m.result_score,
                "note": m.note,
            }
        )
    return ok(data)


@router.post("/makeup")
def create_makeup(
    body: MakeupCreate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    m = MakeupTrack(**body.model_dump())
    db.add(m)
    write_audit(db, "CREATE", "makeup_track", m.id, "补考登记", user.id, request.client.host if request.client else None)
    db.commit()
    return ok({"id": m.id}, message="已登记")


@router.put("/makeup/{makeup_id}")
def update_makeup(
    makeup_id: int,
    body: MakeupUpdate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    m = db.get(MakeupTrack, makeup_id)
    if m is None:
        raise BizError("记录不存在", 404)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(m, k, v)
    # 补考成绩 >= 60 自动判定通过
    if m.result_score is not None and m.result_score >= 60 and m.stage in ("WAIT_MAKEUP", "REMAKEUP_FAIL"):
        m.stage = "MAKEUP_PASSED"
    elif m.result_score is not None and m.result_score < 60 and m.stage in ("WAIT_MAKEUP",):
        m.stage = "REMAKEUP_FAIL"
    db.commit()
    return ok(None, message="已更新")


# ---------- 竞赛获奖 ----------
@router.get("/awards")
def list_awards(
    student_id: int | None = None,
    level: str | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(CompetitionAward)
    if student_id:
        q = q.filter(CompetitionAward.student_id == student_id)
    if level:
        q = q.filter(CompetitionAward.level == level)
    items = q.order_by(CompetitionAward.award_time.desc()).all()
    data = []
    for a in items:
        s = db.get(StudentProfile, a.student_id)
        data.append(
            {
                "id": a.id,
                "student_id": a.student_id,
                "student_name": s.name if s else "",
                "student_no": s.student_no if s else "",
                "event_name": a.event_name,
                "level": a.level,
                "award": a.award,
                "award_time": a.award_time.isoformat() if a.award_time else None,
                "cert_no": a.cert_no,
            }
        )
    return ok(data)


@router.post("/awards")
def create_award(
    body: AwardCreate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a = CompetitionAward(**body.model_dump())
    db.add(a)
    db.commit()
    return ok({"id": a.id}, message="已登记")


# ---------- 证书 ----------
@router.get("/certificates")
def list_certificates(
    student_id: int | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Certificate)
    if student_id:
        q = q.filter(Certificate.student_id == student_id)
    items = q.order_by(Certificate.obtain_time.desc()).all()
    data = []
    for c in items:
        s = db.get(StudentProfile, c.student_id)
        data.append(
            {
                "id": c.id,
                "student_id": c.student_id,
                "student_name": s.name if s else "",
                "student_no": s.student_no if s else "",
                "cert_name": c.cert_name,
                "grade": c.grade,
                "obtain_time": c.obtain_time.isoformat() if c.obtain_time else None,
                "cert_no": c.cert_no,
                "file_url": c.file_url,
            }
        )
    return ok(data)


@router.post("/certificates")
def create_certificate(
    body: CertificateCreate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = Certificate(**body.model_dump())
    db.add(c)
    db.commit()
    return ok({"id": c.id}, message="已登记")
