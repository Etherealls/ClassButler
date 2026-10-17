"""系统底座接口（M4）：账号、审计日志、备份、数据清除"""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, write_audit
from app.core.response import ok
from app.models import (
    Certificate,
    ClassCadre,
    ClassInfo,
    CompetitionAward,
    Course,
    DormAssignment,
    DormRoom,
    DutySchedule,
    FamilyContact,
    QualityEvaluation,
    ScoreRecord,
    SeatPlan,
    StudentProfile,
    SysAuditLog,
    SysUser,
)
from app.schemas import AccountUpdate, ChangePasswordRequest
from app.core.security import hash_password, verify_password
from app.utils import do_backup, list_backups

router = APIRouter(tags=["系统底座"])


# 业务数据表（清除数据时按依赖顺序清空，保留账号与班级）
_DATA_TABLES = [
    FamilyContact,
    ClassCadre,
    DormAssignment,
    DutySchedule,
    ScoreRecord,
    CompetitionAward,
    Certificate,
    QualityEvaluation,
    StudentProfile,
    Course,
    SeatPlan,
    DormRoom,
]


@router.get("/account")
def get_account(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    cls = db.get(ClassInfo, user.class_id) if user.class_id else None
    return ok(
        {
            "id": user.id,
            "username": user.username,
            "phone": user.phone,
            "class_id": user.class_id,
            "class_name": cls.class_name if cls else None,
            "must_change_pwd": user.must_change_pwd,
        }
    )


@router.put("/account")
def update_account(
    body: AccountUpdate,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.phone is not None:
        user.phone = body.phone
    write_audit(db, "UPDATE", "sys_user", user.id, "更新账号信息", user.id, request.client.host if request.client else None)
    db.commit()
    return ok(None, message="已更新")


@router.get("/audit-logs")
def list_audit_logs(
    action: str | None = None,
    page: int = 1,
    size: int = 20,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(SysAuditLog)
    if action:
        q = q.filter(SysAuditLog.action == action)
    total = q.count()
    items = q.order_by(SysAuditLog.id.desc()).offset((page - 1) * size).limit(size).all()
    data = [
        {
            "id": l.id,
            "operator_id": l.operator_id,
            "action": l.action,
            "target_table": l.target_table,
            "target_id": l.target_id,
            "detail": l.detail,
            "ip": l.ip,
            "created_at": l.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for l in items
    ]
    return ok(data, total=total)


@router.get("/backups")
def get_backups(user: SysUser = Depends(get_current_user)):
    return ok(list_backups())


@router.post("/backup")
def create_backup(request: Request, user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    name = do_backup()
    write_audit(db, "BACKUP", None, None, f"手动备份 {name}", user.id, request.client.host if request.client else None)
    db.commit()
    return ok({"name": name}, message="备份完成")


@router.post("/data/clear")
def clear_data(request: Request, user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """清除所有业务数据（保留登录账号与班级）"""
    for table in _DATA_TABLES:
        db.query(table).delete()
    # 清空审计日志
    db.query(SysAuditLog).delete()
    # 写入本次清除操作的审计记录（清空后仅保留这一条）
    write_audit(db, "CLEAR", None, None, "清除全部数据", user.id, request.client.host if request.client else None)
    db.commit()
    return ok(None, message="数据已清除")
