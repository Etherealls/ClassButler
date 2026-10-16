"""纪律记录接口（M2）"""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, write_audit
from app.core.response import BizError, ok
from app.models import DisciplineRecord, StudentProfile, SysUser
from app.schemas import DisciplineCreate
from app.utils import export_rows_to_xlsx

router = APIRouter(prefix="/discipline", tags=["纪律"])

CATEGORIES = ["课堂违纪", "抽烟", "打架", "迟到再犯", "其他"]


@router.post("")
def create_discipline(
    body: DisciplineCreate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.category not in CATEGORIES:
        raise BizError("无效的违纪类型", 400)
    d = DisciplineRecord(**body.model_dump(), recorder_id=user.id)
    db.add(d)
    write_audit(db, "CREATE", "discipline_record", d.id, f"纪律登记 {body.category}", user.id, request.client.host if request.client else None)
    db.commit()
    return ok({"id": d.id}, message="已登记")


@router.get("")
def list_discipline(
    student_id: int | None = None,
    category: str | None = None,
    page: int = 1,
    size: int = 20,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(DisciplineRecord)
    if student_id:
        q = q.filter(DisciplineRecord.student_id == student_id)
    if category:
        q = q.filter(DisciplineRecord.category == category)
    total = q.count()
    items = q.order_by(DisciplineRecord.occur_time.desc()).offset((page - 1) * size).limit(size).all()
    data = []
    for d in items:
        s = db.get(StudentProfile, d.student_id)
        data.append(
            {
                "id": d.id,
                "student_id": d.student_id,
                "student_name": s.name if s else "",
                "student_no": s.student_no if s else "",
                "category": d.category,
                "occur_time": d.occur_time.strftime("%Y-%m-%d %H:%M"),
                "location": d.location,
                "fact": d.fact,
                "result": d.result,
            }
        )
    return ok(data, total=total)


@router.get("/export")
def export_discipline(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(DisciplineRecord).order_by(DisciplineRecord.occur_time.desc()).all()
    headers = ["学号", "姓名", "类型", "时间", "地点", "事实描述", "处理结果"]
    rows = []
    for d in items:
        s = db.get(StudentProfile, d.student_id)
        rows.append(
            [
                s.student_no if s else "",
                s.name if s else "",
                d.category,
                d.occur_time.strftime("%Y-%m-%d %H:%M"),
                d.location or "",
                d.fact,
                d.result or "",
            ]
        )
    content = export_rows_to_xlsx(headers, rows, "纪律台账")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=discipline.xlsx"},
    )
