"""综合素质评价接口（德育/智育/体育/美育/劳育）"""
import random

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, write_audit
from app.core.response import BizError, ok
from app.models import ClassInfo, QualityEvaluation, StudentProfile, SysUser
from app.schemas import QualityEvaluateRequest, QualityManualScore
from app.utils import export_rows_to_xlsx
from app.utils.semester import build_semester_info

router = APIRouter(tags=["综合素质评价"])


def _check_editable_semester(user: SysUser, semester: str):
    """校验学期是否为当前可编辑学期（仅当前学期可修改）"""
    info = build_semester_info(user.start_semester)
    editable = info.get("editable_semester")
    if editable is None:
        raise BizError("请先在账号设置中填写开始担任班主任的学期", 400)
    if semester != editable:
        raise BizError("只能修改当前学期，不能修改其他学期", 400)


def _get_class_id(db: Session, user: SysUser) -> int:
    """确定操作班级：优先账号绑定班级，否则回退第一个班级"""
    if user.class_id is not None:
        return user.class_id
    cls = db.query(ClassInfo).first()
    if cls is None:
        raise BizError("请先创建班级", 400)
    return cls.id


# 等级 -> 合计分区间
LEVEL_RANGE = {
    "优秀": (800, 950),
    "良好": (700, 799),
    "合格": (600, 699),
    "不合格": (0, 599),
}

LEVEL_ORDER = {"优秀": 0, "良好": 1, "合格": 2, "不合格": 3}

# 每个素质单项最高 190 分
MAX_SINGLE = 190


def _gen_scores(student_id: int, level: str) -> tuple[int, int, int, int, int, int]:
    """按等级生成尽量平均的五项整数得分，返回 (moral, intellect, sport, art, labor, total)。

    使用 student_id 作为确定性种子，保证同一学生结果稳定可复现；
    五项围绕同一基准值做极小对称扰动，使五项尽量接近，且全部为整数。
    """
    low, high = LEVEL_RANGE[level]
    # 以区间中值为目标合计，并叠加基于学号的确定性微调
    rng = random.Random(student_id)
    target_total = low + (high - low) * 0.5
    # 微调幅度控制在区间宽度的 8% 内，避免越界
    jitter = (high - low) * 0.08
    total = int(round(target_total + rng.uniform(-jitter, jitter)))
    # 强制落在区间内
    total = max(low, min(high, total))

    base = total // 5
    remainder = total - base * 5  # 0~4，分配到前几项，保证合计精确
    # 对称小扰动 [-2,-1,0,1,2]，保证五项接近且合计准确
    deltas = [-2, -1, 0, 1, 2]
    rng.shuffle(deltas)
    vals = [base + d for d in deltas]
    # 校正扰动带来的偏差，使五项之和精确等于 total
    diff = total - sum(vals)
    vals[0] += diff
    # 每项不超过 190 且不小于 0
    vals = [max(0, min(MAX_SINGLE, v)) for v in vals]
    # 重新归一化确保合计正确（整数）
    adjusted = _normalize_int(vals, total)
    return adjusted[0], adjusted[1], adjusted[2], adjusted[3], adjusted[4], sum(adjusted)


def _normalize_int(vals: list[int], total: int) -> list[int]:
    """确保五项整数之和等于 total"""
    s = sum(vals)
    if s == total:
        return vals
    out = list(vals)
    diff = total - s
    out[0] += diff
    return out


def _gen_scores_by_rank(student_id: int, level: str, rank: int, total_count: int) -> tuple[int, int, int, int, int, int]:
    """按班级排名在等级区间内生成得分。

    排名越靠前，得分越高（在等级对应区间内线性分布），五项尽量平均且为整数。
    """
    low, high = LEVEL_RANGE[level]
    if total_count <= 1:
        total = high
    else:
        # rank 从 1 开始，1 为最高
        ratio = (rank - 1) / (total_count - 1)  # 0(最高) ~ 1(最低)
        total = int(round(high - (high - low) * ratio))
    total = max(low, min(high, total))

    rng = random.Random(student_id + rank * 100000)
    base = total // 5
    deltas = [-2, -1, 0, 1, 2]
    rng.shuffle(deltas)
    vals = [base + d for d in deltas]
    diff = total - sum(vals)
    vals[0] += diff
    vals = [max(0, min(MAX_SINGLE, v)) for v in vals]
    adjusted = _normalize_int(vals, total)
    return adjusted[0], adjusted[1], adjusted[2], adjusted[3], adjusted[4], sum(adjusted)


def _serialize(q: QualityEvaluation, s: StudentProfile | None) -> dict:
    return {
        "id": q.id,
        "student_id": q.student_id,
        "student_name": s.name if s else "",
        "student_no": s.student_no if s else "",
        "semester": q.semester,
        "level": q.level,
        "moral": q.moral,
        "intellect": q.intellect,
        "sport": q.sport,
        "art": q.art,
        "labor": q.labor,
        "total": q.total,
        "rank": q.rank,
        "note": q.note,
    }


def _refresh_ranks(db: Session, semester: str):
    """按学期重排班级排名（合计分降序，同分同名次）"""
    items = (
        db.query(QualityEvaluation)
        .filter(QualityEvaluation.semester == semester)
        .order_by(QualityEvaluation.total.desc(), QualityEvaluation.student_id.asc())
        .all()
    )
    rank = 0
    prev_total = None
    for i, q in enumerate(items, start=1):
        if prev_total is None or q.total != prev_total:
            rank = i
        q.rank = rank
        prev_total = q.total


@router.get("/quality")
def list_quality(
    semester: str | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """综合素质评价列表（含班级排名）"""
    cid = _get_class_id(db, user)
    students = (
        db.query(StudentProfile)
        .filter(StudentProfile.class_id == cid, StudentProfile.deleted_at.is_(None))
        .all()
    )
    student_ids = [s.id for s in students]
    q = db.query(QualityEvaluation).filter(
        QualityEvaluation.student_id.in_(student_ids)
    )
    if semester:
        q = q.filter(QualityEvaluation.semester == semester)
    records = {r.student_id: r for r in q.all()}
    smap = {s.id: s for s in students}

    # 未评价的学生也展示（得分空，便于选择等级）
    data = []
    for sid in student_ids:
        s = smap[sid]
        rec = records.get(sid)
        if rec:
            data.append(_serialize(rec, s))
        else:
            data.append(
                {
                    "id": None,
                    "student_id": sid,
                    "student_name": s.name,
                    "student_no": s.student_no,
                    "semester": semester or "",
                    "level": "",
                    "moral": None,
                    "intellect": None,
                    "sport": None,
                    "art": None,
                    "labor": None,
                    "total": None,
                    "rank": None,
                    "note": None,
                }
            )
    # 按合计分降序、无分者排后
    data.sort(key=lambda x: (x["total"] is None, -(x["total"] or 0)))
    return ok(data)


@router.post("/quality/evaluate")
def evaluate_quality(
    body: QualityEvaluateRequest,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按等级（或按等级+排名）为指定学生（缺省全班级）自动生成五项整数得分并排名"""
    if body.level not in LEVEL_RANGE:
        raise BizError("无效的评价等级", 400)
    _check_editable_semester(user, body.semester)
    cid = _get_class_id(db, user)
    q = db.query(StudentProfile).filter(
        StudentProfile.class_id == cid, StudentProfile.deleted_at.is_(None)
    )
    if body.student_ids:
        q = q.filter(StudentProfile.id.in_(body.student_ids))
    students = q.order_by(StudentProfile.student_no).all()
    if not students:
        raise BizError("没有可评价的学生", 400)

    rank_map = body.rank_map or {}
    # 若提供排名，以排名人数为总数
    total_count = len(students) if not rank_map else max(len(students), 1)

    for s in students:
        sid_key = str(s.id)
        if rank_map and sid_key in rank_map:
            rank = int(rank_map[sid_key])
            moral, intellect, sport, art, labor, total = _gen_scores_by_rank(
                s.id, body.level, rank, total_count
            )
        else:
            moral, intellect, sport, art, labor, total = _gen_scores(s.id, body.level)
        rec = (
            db.query(QualityEvaluation)
            .filter(
                QualityEvaluation.student_id == s.id,
                QualityEvaluation.semester == body.semester,
            )
            .first()
        )
        if rec:
            rec.level = body.level
            rec.moral = moral
            rec.intellect = intellect
            rec.sport = sport
            rec.art = art
            rec.labor = labor
            rec.total = total
        else:
            db.add(
                QualityEvaluation(
                    student_id=s.id,
                    semester=body.semester,
                    level=body.level,
                    moral=moral,
                    intellect=intellect,
                    sport=sport,
                    art=art,
                    labor=labor,
                    total=total,
                )
            )
    db.flush()
    _refresh_ranks(db, body.semester)
    write_audit(db, "EVALUATE", "quality_evaluation", None, f"按等级{body.level}批量评价", user.id, request.client.host if request.client else None)
    db.commit()
    return ok(None, message=f"已按「{body.level}」生成 {len(students)} 名学生的评价得分")


@router.post("/quality/manual")
def manual_quality(
    body: QualityManualScore,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """手动录入/修改单个学生五项得分"""
    s = db.get(StudentProfile, body.student_id)
    if s is None or s.deleted_at is not None:
        raise BizError("学生不存在", 404)
    _check_editable_semester(user, body.semester)
    # 单项得分四舍五入为整数，并校验范围
    moral = int(round(body.moral))
    intellect = int(round(body.intellect))
    sport = int(round(body.sport))
    art = int(round(body.art))
    labor = int(round(body.labor))
    for v in (moral, intellect, sport, art, labor):
        if v < 0 or v > MAX_SINGLE:
            raise BizError(f"单项得分需在 0~{MAX_SINGLE} 之间", 400)
    total = moral + intellect + sport + art + labor
    # 根据合计自动判定等级
    level = ""
    for name, (low, high) in LEVEL_RANGE.items():
        if low <= total <= high:
            level = name
            break
    if not level and total > 950:
        level = "优秀"
    elif not level:
        level = "不合格"

    rec = (
        db.query(QualityEvaluation)
        .filter(
            QualityEvaluation.student_id == body.student_id,
            QualityEvaluation.semester == body.semester,
        )
        .first()
    )
    if rec:
        rec.moral = moral
        rec.intellect = intellect
        rec.sport = sport
        rec.art = art
        rec.labor = labor
        rec.total = total
        rec.level = body.level or level
        rec.note = body.note
    else:
        rec = QualityEvaluation(
            student_id=body.student_id,
            semester=body.semester,
            level=body.level or level,
            moral=moral,
            intellect=intellect,
            sport=sport,
            art=art,
            labor=labor,
            total=total,
            note=body.note,
        )
        db.add(rec)
    db.flush()
    _refresh_ranks(db, body.semester)
    write_audit(db, "UPDATE", "quality_evaluation", rec.id, "手动录入素质得分", user.id, request.client.host if request.client else None)
    db.commit()
    return ok(None, message="已保存")


@router.delete("/quality/{student_id}")
def delete_quality(
    student_id: int,
    request: Request,
    semester: str = Query(...),
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除某学生某学期的评价记录"""
    rec = (
        db.query(QualityEvaluation)
        .filter(
            QualityEvaluation.student_id == student_id,
            QualityEvaluation.semester == semester,
        )
        .first()
    )
    if rec:
        db.delete(rec)
        write_audit(db, "DELETE", "quality_evaluation", rec.id, "删除素质评价", user.id, request.client.host if request.client else None)
        db.commit()
        _refresh_ranks(db, semester)
        db.commit()
    return ok(None, message="已删除")


@router.get("/quality/export")
def export_quality(
    semester: str | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出综合素质评价为 Excel"""
    data = list_quality(semester=semester, user=user, db=db)["data"]
    headers = ["序号", "学生姓名", "学生学号", "德育", "智育", "体育", "美育", "劳育", "合计", "班级排名", "综合评价等级"]
    rows = []
    for i, d in enumerate(data, start=1):
        if d["total"] is None:
            continue
        rows.append(
            [
                i,
                d["student_name"],
                d["student_no"],
                d["moral"],
                d["intellect"],
                d["sport"],
                d["art"],
                d["labor"],
                d["total"],
                d["rank"],
                d["level"],
            ]
        )
    content = export_rows_to_xlsx(headers, rows, "综合素质评价")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=quality_evaluation.xlsx"},
    )
