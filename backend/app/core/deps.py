"""FastAPI 依赖：认证、审计、当前用户"""
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import BizError
from app.core.security import decode_token
from app.models import SysAuditLog, SysUser

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> SysUser:
    if credentials is None:
        raise BizError("未登录或令牌缺失", 401)
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise BizError("令牌无效或已过期", 401)
    user = db.get(SysUser, int(payload["sub"]))
    if user is None or user.deleted_at is not None or user.status != "ACTIVE":
        raise BizError("账号不存在或已停用", 401)
    return user


def write_audit(
    db: Session,
    action: str,
    target_table: str | None = None,
    target_id: int | None = None,
    detail: str | None = None,
    operator_id: int | None = None,
    ip: str | None = None,
):
    log = SysAuditLog(
        operator_id=operator_id,
        action=action,
        target_table=target_table,
        target_id=target_id,
        detail=detail,
        ip=ip,
    )
    db.add(log)
