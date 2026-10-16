"""请假接口（M2）"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, write_audit
from app.core.response import BizError, ok
from app.models import LeaveRequest, StudentProfile, SysUser
from app.schemas import LeaveCreate, LeaveUpdate
from app.utils import export_rows_to_xlsx

router = APIRouter(prefix="/leaves", tags=["请假"])

TYPE_LABEL = {"PERSONAL": "事假", "SICK": "病假", "PUBLIC": "公假"}
STATUS_LABEL = {"LEAVING": "请假中", "FINISHED": "已结束"}


@router.post("")
def create_leave(
    body: LeaveCreate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.leave_type not in TYPE_LABEL:
        raise BizError("无效的请假类型", 400)
    if body.end_time <= body.start_time:
        raise BizError("结束时间必须晚于开始时间", 400)
    lv = LeaveRequest(**body.model_dump(), status="LEAVING")
    db.add(lv)
    write_audit(db, "CREATE", "leave_request", lv.id, "登记请假", user.id, request.client.host if request.client else None)
    db.commit()
    db.refresh(lv)
    return ok({"id": lv.id, "status": lv.status}, message="请假已登记")


@router.get("")
def list_leaves(
    student_id: int | None = None,
    leave_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    size: int = 20,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(LeaveRequest)
    if student_id:
        q = q.filter(LeaveRequest.student_id == student_id)
    if leave_type:
        q = q.filter(LeaveRequest.leave_type == leave_type)
    if status:
        q = q.filter(LeaveRequest.status == status)
    total = q.count()
    items = q.order_by(LeaveRequest.start_time.desc()).offset((page - 1) * size).limit(size).all()
    data = []
    for lv in items:
        s = db.get(StudentProfile, lv.student_id)
        # 逾期未归提示
        overdue = lv.status == "LEAVING" and lv.end_time < datetime.now()
        data.append(
            {
                "id": lv.id,
                "student_id": lv.student_id,
                "student_name": s.name if s else "",
                "student_no": s.student_no if s else "",
                "leave_type": lv.leave_type,
                "leave_type_label": TYPE_LABEL.get(lv.leave_type, lv.leave_type),
                "start_time": lv.start_time.strftime("%Y-%m-%d %H:%M"),
                "end_time": lv.end_time.strftime("%Y-%m-%d %H:%M"),
                "duration_hours": lv.duration_hours,
                "destination": lv.destination,
                "reason": lv.reason,
                "status": lv.status,
                "status_label": STATUS_LABEL.get(lv.status, lv.status),
                "overdue": overdue,
                "note": lv.note,
            }
        )
    return ok(data, total=total)


@router.put("/{leave_id}")
def update_leave(
    leave_id: int,
    body: LeaveUpdate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lv = db.get(LeaveRequest, leave_id)
    if lv is None:
        raise BizError("请假记录不存在", 404)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(lv, k, v)
    write_audit(db, "UPDATE", "leave_request", lv.id, "更新请假", user.id, request.client.host if request.client else None)
    db.commit()
    return ok(None, message="已更新")


@router.get("/export")
def export_leaves(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(LeaveRequest).order_by(LeaveRequest.start_time.desc()).all()
    headers = ["学号", "姓名", "类型", "开始时间", "结束时间", "时长(小时)", "去向", "事由", "状态"]
    rows = []
    for lv in items:
        s = db.get(StudentProfile, lv.student_id)
        rows.append(
            [
                s.student_no if s else "",
                s.name if s else "",
                TYPE_LABEL.get(lv.leave_type, lv.leave_type),
                lv.start_time.strftime("%Y-%m-%d %H:%M"),
                lv.end_time.strftime("%Y-%m-%d %H:%M"),
                lv.duration_hours,
                lv.destination or "",
                lv.reason,
                STATUS_LABEL.get(lv.status, lv.status),
            ]
        )
    content = export_rows_to_xlsx(headers, rows, "请假台账")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=leaves.xlsx"},
    )
