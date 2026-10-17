"""学生档案接口（M1）"""
from datetime import datetime

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, write_audit
from app.core.response import BizError, ok
from app.models import ClassInfo, FamilyContact, StudentProfile, SysUser
from app.schemas import FamilyContactIn, StudentCreate, StudentUpdate
from app.utils import export_rows_to_xlsx, parse_xlsx, serialize_student

router = APIRouter(prefix="/students", tags=["学生档案"])


def _get_class_id(db: Session, user: SysUser, class_id: int | None) -> int:
    """确定操作班级：优先传入 class_id，否则用账号绑定班级"""
    if class_id is not None:
        return class_id
    if user.class_id is not None:
        return user.class_id
    cls = db.query(ClassInfo).first()
    if cls is None:
        raise BizError("请先创建班级", 400)
    return cls.id


def _check_unique(db: Session, student_no: str, class_id: int, exclude_id: int | None = None):
    q = db.query(StudentProfile).filter(
        StudentProfile.class_id == class_id,
        StudentProfile.student_no == student_no,
        StudentProfile.deleted_at.is_(None),
    )
    if exclude_id:
        q = q.filter(StudentProfile.id != exclude_id)
    if q.first():
        raise BizError(f"学号 {student_no} 在该班级已存在", 400)


@router.get("")
def list_students(
    keyword: str | None = None,
    gender: str | None = None,
    class_id: int | None = None,
    native_place: str | None = None,
    origin: str | None = None,
    page: int = 1,
    size: int = 20,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = _get_class_id(db, user, class_id)
    q = db.query(StudentProfile).filter(
        StudentProfile.class_id == cid, StudentProfile.deleted_at.is_(None)
    )
    if keyword:
        q = q.filter(
            or_(
                StudentProfile.name.like(f"%{keyword}%"),
                StudentProfile.student_no.like(f"%{keyword}%"),
            )
        )
    if gender:
        q = q.filter(StudentProfile.gender == gender)
    if native_place:
        q = q.filter(StudentProfile.native_place == native_place)
    if origin:
        q = q.filter(StudentProfile.origin == origin)
    total = q.count()
    items = (
        q.order_by(StudentProfile.student_no)
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return ok([serialize_student(s, mask=True) for s in items], total=total)


@router.post("")
def create_student(
    body: StudentCreate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = _get_class_id(db, user, body.class_id)
    _check_unique(db, body.student_no, cid)
    s = StudentProfile(**body.model_dump(exclude={"class_id", "family_contacts"}), class_id=cid)
    db.add(s)
    db.flush()
    for f in body.family_contacts:
        db.add(FamilyContact(student_id=s.id, **f.model_dump()))
    write_audit(db, "CREATE", "student_profile", s.id, f"建档 {body.name}", user.id, request.client.host if request.client else None)
    db.commit()
    db.refresh(s)
    return ok(serialize_student(s), message="建档成功")


# ---------- 导入 / 导出 / 模板（静态路由需在动态路由之前定义） ----------
@router.get("/template")
def download_template(user: SysUser = Depends(get_current_user)):
    headers = [
        "学号", "姓名", "性别", "出生日期", "身份证号", "民族", "政治面貌",
        "籍贯", "生源地", "手机号", "家庭住址", "紧急联系人", "紧急联系电话",
        "家庭情况备注",
    ]
    rows = [["2026001", "张三", "男", "2006-01-15", "", "汉族", "群众", "", "", "", "", "", "", ""]]
    content = export_rows_to_xlsx(headers, rows, "学生档案模板")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=students_template.xlsx"},
    )


@router.post("/import")
async def import_students(
    file: UploadFile = File(...),
    class_id: int | None = Query(None),
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = _get_class_id(db, user, class_id)
    content = await file.read()
    rows = parse_xlsx(content)
    if not rows:
        raise BizError("文件为空或格式错误", 400)
    success, errors = 0, []
    for idx, r in enumerate(rows, start=2):
        student_no = str(r.get("学号", "") or "").strip()
        name = str(r.get("姓名", "") or "").strip()
        gender = str(r.get("性别", "") or "").strip()
        if not student_no or not name or not gender:
            errors.append({"row": idx, "reason": "学号/姓名/性别为必填"})
            continue
        if gender not in ("男", "女"):
            errors.append({"row": idx, "reason": f"性别无效: {gender}"})
            continue
        if db.query(StudentProfile).filter(
            StudentProfile.class_id == cid,
            StudentProfile.student_no == student_no,
            StudentProfile.deleted_at.is_(None),
        ).first():
            errors.append({"row": idx, "reason": f"学号 {student_no} 已存在"})
            continue
        db.add(
            StudentProfile(
                student_no=student_no,
                name=name,
                gender=gender,
                birth_date=_parse_date(r.get("出生日期")),
                id_card=str(r.get("身份证号", "") or "").strip() or None,
                nation=str(r.get("民族", "") or "").strip() or None,
                political=str(r.get("政治面貌", "") or "").strip() or None,
                native_place=str(r.get("籍贯", "") or "").strip() or None,
                origin=str(r.get("生源地", "") or "").strip() or None,
                phone=str(r.get("手机号", "") or "").strip() or None,
                address=str(r.get("家庭住址", "") or "").strip() or None,
                emergency_name=str(r.get("紧急联系人", "") or "").strip() or None,
                emergency_phone=str(r.get("紧急联系电话", "") or "").strip() or None,
                family_note=str(r.get("家庭情况备注", "") or "").strip() or None,
                class_id=cid,
            )
        )
        success += 1
    db.commit()
    return ok({"success": success, "errors": errors}, message=f"成功导入 {success} 条")


@router.get("/export")
def export_students(
    class_id: int | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = _get_class_id(db, user, class_id)
    students = (
        db.query(StudentProfile)
        .filter(StudentProfile.class_id == cid, StudentProfile.deleted_at.is_(None))
        .order_by(StudentProfile.student_no)
        .all()
    )
    headers = ["学号", "姓名", "性别", "出生日期", "民族", "政治面貌", "籍贯", "生源地", "手机号", "家庭住址"]
    rows = [
        [
            s.student_no, s.name, s.gender,
            s.birth_date.isoformat() if s.birth_date else "",
            s.nation or "", s.political or "", s.native_place or "",
            s.origin or "", s.phone or "", s.address or "",
        ]
        for s in students
    ]
    content = export_rows_to_xlsx(headers, rows, "花名册")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=roster.xlsx"},
    )


@router.get("/{student_id}")
def get_student(
    student_id: int,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.get(StudentProfile, student_id)
    if s is None or s.deleted_at is not None:
        raise BizError("学生不存在", 404)
    return ok(serialize_student(s))


@router.put("/{student_id}")
def update_student(
    student_id: int,
    body: StudentUpdate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.get(StudentProfile, student_id)
    if s is None or s.deleted_at is not None:
        raise BizError("学生不存在", 404)
    data = body.model_dump(exclude_unset=True)
    if "class_id" in data and data["class_id"] is not None:
        _check_unique(db, data.get("student_no", s.student_no), data["class_id"], s.id)
    elif "student_no" in data:
        _check_unique(db, data["student_no"], s.class_id, s.id)
    for k, v in data.items():
        setattr(s, k, v)
    write_audit(db, "UPDATE", "student_profile", s.id, f"编辑 {s.name}", user.id, request.client.host if request.client else None)
    db.commit()
    db.refresh(s)
    return ok(serialize_student(s), message="更新成功")


@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.get(StudentProfile, student_id)
    if s is None or s.deleted_at is not None:
        raise BizError("学生不存在", 404)
    s.deleted_at = datetime.now()
    write_audit(db, "DELETE", "student_profile", s.id, f"删除 {s.name}", user.id, request.client.host if request.client else None)
    db.commit()
    return ok(None, message="已删除")


@router.post("/{student_id}/family")
def add_family(
    student_id: int,
    body: FamilyContactIn,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.get(StudentProfile, student_id)
    if s is None or s.deleted_at is not None:
        raise BizError("学生不存在", 404)
    count = db.query(FamilyContact).filter(FamilyContact.student_id == student_id).count()
    if count >= 2:
        raise BizError("每名学生最多登记 2 名家长", 400)
    db.add(FamilyContact(student_id=student_id, **body.model_dump()))
    write_audit(db, "CREATE", "family_contact", student_id, f"新增家长 {body.parent_name}", user.id, request.client.host if request.client else None)
    db.commit()
    return ok(None, message="已添加")


def _parse_date(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None
