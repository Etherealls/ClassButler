"""班级组织接口（M1）：干部名册、宿舍分配、座位表、值日排班、班级信息"""
import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, write_audit
from app.core.response import BizError, ok
from app.models import (
    ClassCadre,
    ClassInfo,
    DormAssignment,
    DormRoom,
    DutySchedule,
    SeatPlan,
    StudentProfile,
    SysUser,
)
from app.schemas import (
    CadreCreate,
    ClassInfoCreate,
    DormAssignCreate,
    DutyScheduleCreate,
    SeatPlanSave,
)

router = APIRouter(tags=["班级组织"])


# ---------- 班级 ----------
@router.get("/classes")
def list_classes(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    classes = db.query(ClassInfo).filter(ClassInfo.deleted_at.is_(None)).all()
    return ok(
        [
            {"id": c.id, "class_name": c.class_name, "grade_year": c.grade_year, "major": c.major}
            for c in classes
        ]
    )


@router.post("/classes")
def create_class(
    body: ClassInfoCreate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = ClassInfo(**body.model_dump(), head_teacher_user_id=user.id)
    db.add(c)
    db.commit()
    db.refresh(c)
    write_audit(db, "CREATE", "class_info", c.id, f"创建班级 {c.class_name}", user.id, request.client.host if request.client else None)
    db.commit()
    return ok({"id": c.id}, message="班级已创建")


# ---------- 学生干部 ----------
@router.get("/cadres")
def list_cadres(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(ClassCadre).order_by(ClassCadre.start_date.desc()).all()
    data = []
    for c in items:
        s = db.get(StudentProfile, c.student_id)
        data.append(
            {
                "id": c.id,
                "student_id": c.student_id,
                "student_name": s.name if s else "",
                "student_no": s.student_no if s else "",
                "position": c.position,
                "start_date": c.start_date.isoformat() if c.start_date else None,
                "end_date": c.end_date.isoformat() if c.end_date else None,
            }
        )
    return ok(data)


@router.post("/cadres")
def create_cadre(
    body: CadreCreate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = ClassCadre(**body.model_dump())
    db.add(c)
    write_audit(db, "CREATE", "class_cadre", c.id, f"干部登记 {body.position}", user.id, request.client.host if request.client else None)
    db.commit()
    return ok({"id": c.id}, message="已登记")


# ---------- 宿舍 ----------
@router.get("/dorm/rooms")
def list_dorm_rooms(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    rooms = db.query(DormRoom).all()
    return ok([{"id": r.id, "room_no": r.room_no, "capacity": r.capacity} for r in rooms])


@router.post("/dorm/rooms")
def create_dorm_room(
    body: dict,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room_no = body.get("room_no")
    capacity = body.get("capacity", 4)
    if db.query(DormRoom).filter(DormRoom.room_no == room_no).first():
        raise BizError("宿舍号已存在", 400)
    r = DormRoom(room_no=room_no, capacity=capacity)
    db.add(r)
    db.commit()
    return ok({"id": r.id}, message="宿舍已创建")


@router.get("/dorm/assignments")
def list_dorm_assignments(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(DormAssignment).filter(DormAssignment.end_date.is_(None)).all()
    data = []
    for a in items:
        s = db.get(StudentProfile, a.student_id)
        data.append(
            {
                "id": a.id,
                "student_id": a.student_id,
                "student_name": s.name if s else "",
                "student_no": s.student_no if s else "",
                "room_no": a.room_no,
                "bed_no": a.bed_no,
                "start_date": a.start_date.isoformat() if a.start_date else None,
            }
        )
    return ok(data)


@router.post("/dorm/assignments")
def create_dorm_assignment(
    body: DormAssignCreate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 调宿：结束原有分配
    existing = (
        db.query(DormAssignment)
        .filter(DormAssignment.student_id == body.student_id, DormAssignment.end_date.is_(None))
        .first()
    )
    if existing:
        existing.end_date = body.start_date
    a = DormAssignment(**body.model_dump())
    db.add(a)
    write_audit(db, "CREATE", "dorm_assignment", a.id, f"分配宿舍 {body.room_no}", user.id, request.client.host if request.client else None)
    db.commit()
    return ok({"id": a.id}, message="已分配")


# ---------- 座位表 ----------
@router.get("/seat-plan")
def get_seat_plan(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.query(SeatPlan).filter(SeatPlan.is_current.is_(True)).order_by(SeatPlan.version.desc()).first()
    if plan is None:
        return ok(None)
    return ok(
        {
            "id": plan.id,
            "version": plan.version,
            "rows": plan.rows,
            "cols": plan.cols,
            "layout": json.loads(plan.layout) if plan.layout else {},
        }
    )


@router.post("/seat-plan")
def save_seat_plan(
    body: SeatPlanSave,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(SeatPlan).filter(SeatPlan.is_current.is_(True)).update({"is_current": False})
    last = db.query(SeatPlan).order_by(SeatPlan.version.desc()).first()
    version = (last.version + 1) if last else 1
    plan = SeatPlan(
        version=version,
        rows=body.rows,
        cols=body.cols,
        layout=json.dumps(body.layout, ensure_ascii=False),
        is_current=True,
    )
    db.add(plan)
    write_audit(db, "CREATE", "seat_plan", None, f"保存座位表 v{version}", user.id, request.client.host if request.client else None)
    db.commit()
    return ok({"version": version}, message="座位表已保存")


# ---------- 值日排班 ----------
DUTY_JOBS = ["扫地", "拖地", "擦黑板", "整理讲台窗台", "刷地"]


@router.get("/duty-schedule")
def list_duty(
    weekday: int | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(DutySchedule)
    if weekday:
        q = q.filter(DutySchedule.weekday == weekday)
    items = q.order_by(DutySchedule.weekday).all()
    data = []
    for d in items:
        ids = [int(x) for x in d.student_ids.split(",") if x.strip()]
        jobs = json.loads(d.jobs) if d.jobs else {}
        students = []
        for sid in ids:
            s = db.get(StudentProfile, sid)
            students.append(
                {
                    "id": sid,
                    "name": s.name if s else "",
                    "student_no": s.student_no if s else "",
                    "job": jobs.get(str(sid), ""),
                }
            )
        data.append(
            {
                "id": d.id,
                "weekday": d.weekday,
                "students": students,
                "note": d.note,
            }
        )
    return ok(data)


@router.post("/duty-schedule")
def create_duty(
    body: DutyScheduleCreate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = DutySchedule(
        weekday=body.weekday,
        student_ids=",".join(str(x) for x in body.student_ids),
        jobs=json.dumps(body.jobs or {}, ensure_ascii=False),
        note=body.note,
    )
    db.add(d)
    db.commit()
    return ok({"id": d.id}, message="已排班")
