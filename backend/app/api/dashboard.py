"""数据看板接口（M4）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.response import ok
from app.models import (
    Certificate,
    ClassCadre,
    ClassInfo,
    CompetitionAward,
    DormAssignment,
    QualityEvaluation,
    StudentProfile,
    SysUser,
)

router = APIRouter(prefix="/dashboard", tags=["看板"])


def _get_class_id(db: Session, user: SysUser) -> int:
    if user.class_id is not None:
        return user.class_id
    cls = db.query(ClassInfo).first()
    return cls.id if cls else 0


@router.get("/overview")
def overview(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = _get_class_id(db, user)
    total_students = db.query(StudentProfile).filter(
        StudentProfile.class_id == cid, StudentProfile.deleted_at.is_(None)
    ).count()

    # 干部人数
    cadre_ids = {c.student_id for c in db.query(ClassCadre).all()}
    student_ids = {
        s.id
        for s in db.query(StudentProfile).filter(
            StudentProfile.class_id == cid, StudentProfile.deleted_at.is_(None)
        ).all()
    }
    cadre_count = len(cadre_ids & student_ids)

    # 宿舍数
    dorm_count = db.query(DormAssignment).filter(DormAssignment.end_date.is_(None)).count()

    # 荣誉/证书数（本班学生）
    award_count = db.query(CompetitionAward).filter(
        CompetitionAward.student_id.in_(student_ids)
    ).count()
    cert_count = db.query(Certificate).filter(
        Certificate.student_id.in_(student_ids)
    ).count()

    # 综合素质评价统计
    quality = db.query(QualityEvaluation).filter(
        QualityEvaluation.student_id.in_(student_ids)
    ).all()
    level_count = {"优秀": 0, "良好": 0, "合格": 0, "不合格": 0}
    for q in quality:
        if q.level in level_count:
            level_count[q.level] += 1
    evaluated = len(quality)
    unevaluated = total_students - evaluated

    return ok(
        {
            "total_students": total_students,
            "cadre_count": cadre_count,
            "dorm_count": dorm_count,
            "award_count": award_count,
            "cert_count": cert_count,
            "evaluated": evaluated,
            "unevaluated": unevaluated,
            "level_count": level_count,
        }
    )


@router.get("/quality-distribution")
def quality_distribution(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """综合素质评价等级分布"""
    cid = _get_class_id(db, user)
    student_ids = {
        s.id
        for s in db.query(StudentProfile).filter(
            StudentProfile.class_id == cid, StudentProfile.deleted_at.is_(None)
        ).all()
    }
    quality = db.query(QualityEvaluation).filter(
        QualityEvaluation.student_id.in_(student_ids)
    ).all()
    level_count = {"优秀": 0, "良好": 0, "合格": 0, "不合格": 0}
    for q in quality:
        if q.level in level_count:
            level_count[q.level] += 1
    return ok(
        [
            {"name": name, "value": level_count[name]}
            for name in ["优秀", "良好", "合格", "不合格"]
        ]
    )


@router.get("/honor-top")
def honor_top(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """荣誉（竞赛+证书）数量 Top 榜"""
    cid = _get_class_id(db, user)
    student_ids = {
        s.id
        for s in db.query(StudentProfile).filter(
            StudentProfile.class_id == cid, StudentProfile.deleted_at.is_(None)
        ).all()
    }
    counts: dict[int, int] = {}
    for a in db.query(CompetitionAward).filter(CompetitionAward.student_id.in_(student_ids)).all():
        counts[a.student_id] = counts.get(a.student_id, 0) + 1
    for c in db.query(Certificate).filter(Certificate.student_id.in_(student_ids)).all():
        counts[c.student_id] = counts.get(c.student_id, 0) + 1
    top = sorted(counts.items(), key=lambda x: -x[1])[:10]

    def _name(sid):
        s = db.get(StudentProfile, sid)
        return s.name if s else ""

    return ok([{"student_id": sid, "name": _name(sid), "count": cnt} for sid, cnt in top])
