"""查寝接口（M2）"""
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, write_audit
from app.core.response import BizError, ok
from app.models import DormAssignment, DormCheck, StudentProfile, SysUser
from app.schemas import DormCheckBatchRequest
from app.utils import export_rows_to_xlsx

router = APIRouter(prefix="/dorm-check", tags=["查寝"])

STATUS_LABEL = {"IN": "在寝", "LATE_BACK": "晚归", "NOT_IN": "未归", "APPROVED_OUT": "外宿"}


@router.post("/batch")
def batch_dorm_check(
    body: DormCheckBatchRequest,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 根据 records 里的 student_id 登记；房间号取自当前宿舍分配
    for student_id, status in body.records.items():
        if status not in STATUS_LABEL:
            raise BizError(f"无效的查寝状态: {status}", 400)
        assign = (
            db.query(DormAssignment)
            .filter(DormAssignment.student_id == student_id, DormAssignment.end_date.is_(None))
            .first()
        )
        room_no = assign.room_no if assign else "未分配"
        existing = (
            db.query(DormCheck)
            .filter(
                DormCheck.student_id == student_id,
                DormCheck.check_date == body.check_date,
            )
            .first()
        )
        if existing:
            existing.status = status
            existing.room_no = room_no
            existing.remark = body.remark
        else:
            db.add(
                DormCheck(
                    student_id=student_id,
                    room_no=room_no,
                    check_date=body.check_date,
                    status=status,
                    remark=body.remark,
                    checker_id=user.id,
                )
            )
    write_audit(db, "CREATE", "dorm_check", None, f"夜查 {body.check_date}", user.id, request.client.host if request.client else None)
    db.commit()
    return ok(None, message="查寝已保存")


@router.get("")
def list_dorm_check(
    check_date: date | None = None,
    status: str | None = None,
    abnormal: bool = False,
    page: int = 1,
    size: int = 50,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(DormCheck)
    if check_date:
        q = q.filter(DormCheck.check_date == check_date)
    if status:
        q = q.filter(DormCheck.status == status)
    if abnormal:
        q = q.filter(DormCheck.status.in_(["LATE_BACK", "NOT_IN"]))
    total = q.count()
    items = q.order_by(DormCheck.check_date.desc()).offset((page - 1) * size).limit(size).all()
    data = []
    for r in items:
        s = db.get(StudentProfile, r.student_id)
        data.append(
            {
                "id": r.id,
                "student_id": r.student_id,
                "student_name": s.name if s else "",
                "student_no": s.student_no if s else "",
                "room_no": r.room_no,
                "check_date": r.check_date.isoformat() if r.check_date else None,
                "status": r.status,
                "status_label": STATUS_LABEL.get(r.status, r.status),
                "remark": r.remark,
            }
        )
    return ok(data, total=total)


@router.get("/export")
def export_dorm_check(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(DormCheck).order_by(DormCheck.check_date.desc()).all()
    headers = ["日期", "宿舍", "学号", "姓名", "状态", "备注"]
    rows = []
    for r in items:
        s = db.get(StudentProfile, r.student_id)
        rows.append(
            [
                r.check_date.isoformat() if r.check_date else "",
                r.room_no,
                s.student_no if s else "",
                s.name if s else "",
                STATUS_LABEL.get(r.status, r.status),
                r.remark or "",
            ]
        )
    content = export_rows_to_xlsx(headers, rows, "查寝台账")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=dorm_check.xlsx"},
    )
