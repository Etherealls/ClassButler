"""成绩、课程接口（M3）"""
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, write_audit
from app.core.response import BizError, ok
from app.models import Course, ScoreRecord, StudentProfile, SysUser
from app.schemas import CourseCreate, ScoreUpdate
from app.utils import export_rows_to_xlsx, parse_xlsx
from app.utils.semester import build_semester_info

router = APIRouter(tags=["成绩"])


def _check_editable_semester(user: SysUser, semester: str):
    """校验学期是否为当前可编辑学期（仅当前学期可修改）"""
    info = build_semester_info(user.start_semester)
    editable = info.get("editable_semester")
    if editable is None:
        raise BizError("请先在账号设置中填写开始担任班主任的学期", 400)
    if semester != editable:
        raise BizError("只能修改当前学期，不能修改其他学期", 400)


# ---------- 课程 ----------
@router.get("/courses")
def list_courses(
    semester: str | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Course)
    if semester:
        q = q.filter(Course.semester == semester)
    items = q.order_by(Course.semester.desc()).all()
    return ok(
        [
            {"id": c.id, "course_name": c.course_name, "semester": c.semester, "credit": c.credit}
            for c in items
        ]
    )


@router.post("/courses")
def create_course(
    body: CourseCreate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_editable_semester(user, body.semester)
    c = Course(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return ok({"id": c.id}, message="课程已添加")


# ---------- 成绩 ----------
@router.get("/scores")
def list_scores(
    semester: str | None = None,
    course_id: int | None = None,
    student_id: int | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """成绩列表 + 排名 + 统计"""
    if not semester:
        raise BizError("请指定学期", 400)
    students = (
        db.query(StudentProfile)
        .filter(StudentProfile.deleted_at.is_(None))
        .order_by(StudentProfile.student_no)
        .all()
    )
    courses = db.query(Course).filter(Course.semester == semester).all()
    course_ids = [c.id for c in courses]

    # 成绩映射：student_id -> {course_id: score}
    score_map: dict[int, dict[int, float]] = {}
    scores = db.query(ScoreRecord).filter(ScoreRecord.semester == semester).all()
    for sc in scores:
        score_map.setdefault(sc.student_id, {})[sc.course_id] = sc.score

    result = []
    for s in students:
        row = {
            "student_id": s.id,
            "student_name": s.name,
            "student_no": s.student_no,
            "scores": {cid: score_map.get(s.id, {}).get(cid) for cid in course_ids},
            "total": None,
            "average": None,
            "rank": None,
            "fail_count": 0,
        }
        valid = [v for v in row["scores"].values() if v is not None]
        if valid:
            row["total"] = round(sum(valid), 1)
            row["average"] = round(sum(valid) / len(valid), 2)
            row["fail_count"] = sum(1 for v in valid if v < 60)
        result.append(row)

    # 排名（按总分降序）
    ranked = sorted(
        [r for r in result if r["total"] is not None],
        key=lambda x: x["total"],
        reverse=True,
    )
    for i, r in enumerate(ranked):
        r["rank"] = i + 1

    # 统计
    stats = {"avg": None, "max": None, "min": None, "pass_rate": None, "excellent_rate": None}
    all_avg = [r["average"] for r in result if r["average"] is not None]
    if all_avg:
        stats["avg"] = round(sum(all_avg) / len(all_avg), 2)
        stats["max"] = max(all_avg)
        stats["min"] = min(all_avg)
        pass_count = sum(1 for a in all_avg if a >= 60)
        stats["pass_rate"] = round(pass_count / len(all_avg) * 100, 2)
        excellent_count = sum(1 for a in all_avg if a >= 85)
        stats["excellent_rate"] = round(excellent_count / len(all_avg) * 100, 2)

    return ok(
        {
            "courses": [
                {"id": c.id, "course_name": c.course_name, "credit": c.credit} for c in courses
            ],
            "students": result,
            "stats": stats,
        }
    )


@router.put("/scores/{score_id}")
def update_score(
    score_id: int,
    body: ScoreUpdate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (0 <= body.score <= 100):
        raise BizError("分数必须在 0-100 之间", 400)
    sc = db.get(ScoreRecord, score_id)
    if sc is None:
        raise BizError("成绩记录不存在", 404)
    old = sc.score
    sc.score = body.score
    write_audit(db, "UPDATE", "score_record", sc.id, f"成绩修改 旧:{old} 新:{body.score}", user.id, request.client.host if request.client else None)
    db.commit()
    return ok(None, message="成绩已更新")


@router.post("/scores/import")
async def import_scores(
    file: UploadFile = File(...),
    semester: str = Query(...),
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_editable_semester(user, semester)
    content = await file.read()
    rows = parse_xlsx(content)
    if not rows:
        raise BizError("文件为空或格式错误", 400)
    if "学号" not in rows[0]:
        raise BizError("缺少「学号」列", 400)
    course_names = [h for h in rows[0].keys() if h not in ("学号", "姓名")]
    if not course_names:
        raise BizError("缺少课程列", 400)

    # 确保课程存在
    course_map = {}
    for cn in course_names:
        c = db.query(Course).filter(Course.course_name == cn, Course.semester == semester).first()
        if c is None:
            c = Course(course_name=cn, semester=semester)
            db.add(c)
            db.flush()
        course_map[cn] = c.id

    success, errors = 0, []
    for idx, r in enumerate(rows, start=2):
        student_no = str(r.get("学号", "") or "").strip()
        s = db.query(StudentProfile).filter(StudentProfile.student_no == student_no, StudentProfile.deleted_at.is_(None)).first()
        if s is None:
            errors.append({"row": idx, "reason": f"学号 {student_no} 不存在"})
            continue
        for cn, cid in course_map.items():
            raw = r.get(cn)
            if raw is None or str(raw).strip() == "":
                continue
            try:
                score = float(raw)
            except (ValueError, TypeError):
                errors.append({"row": idx, "reason": f"课程 {cn} 分数无效: {raw}"})
                continue
            if not (0 <= score <= 100):
                errors.append({"row": idx, "reason": f"课程 {cn} 分数越界: {score}"})
                continue
            existing = (
                db.query(ScoreRecord)
                .filter(
                    ScoreRecord.student_id == s.id,
                    ScoreRecord.course_id == cid,
                    ScoreRecord.semester == semester,
                )
                .first()
            )
            if existing:
                existing.score = score
            else:
                db.add(ScoreRecord(student_id=s.id, course_id=cid, semester=semester, score=score))
            success += 1
    db.commit()
    return ok({"success": success, "errors": errors}, message=f"导入成功 {success} 条")


@router.get("/scores/export")
def export_scores(
    semester: str = Query(...),
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    students = db.query(StudentProfile).filter(StudentProfile.deleted_at.is_(None)).order_by(StudentProfile.student_no).all()
    courses = db.query(Course).filter(Course.semester == semester).all()
    score_map = {}
    for sc in db.query(ScoreRecord).filter(ScoreRecord.semester == semester).all():
        score_map.setdefault(sc.student_id, {})[sc.course_id] = sc.score

    headers = ["学号", "姓名"] + [c.course_name for c in courses] + ["总分", "平均分"]
    rows = []
    for s in students:
        sc = [score_map.get(s.id, {}).get(c.id, "") for c in courses]
        valid = [v for v in sc if v is not None and v != ""]
        total = round(sum(valid), 1) if valid else ""
        avg = round(sum(valid) / len(valid), 2) if valid else ""
        rows.append([s.student_no, s.name] + sc + [total, avg])
    content = export_rows_to_xlsx(headers, rows, "成绩表")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=scores_{semester}.xlsx"},
    )
