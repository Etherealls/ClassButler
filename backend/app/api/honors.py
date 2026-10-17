"""荣誉（竞赛/证书）接口（M3）"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.response import ok
from app.models import (
    Certificate,
    CompetitionAward,
    StudentProfile,
    SysUser,
)
from app.schemas import (
    AwardCreate,
    CertificateCreate,
)

router = APIRouter(tags=["荣誉"])


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
