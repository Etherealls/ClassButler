"""认证接口"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, write_audit
from app.core.response import BizError, ok
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import SysUser
from app.schemas import ChangePasswordRequest, LoginRequest, RefreshRequest

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(SysUser).filter(SysUser.username == body.username).first()
    if user is None or user.deleted_at is not None:
        raise BizError("账号或密码错误", 400)
    if not verify_password(body.password, user.password_hash):
        raise BizError("账号或密码错误", 400)
    if user.status != "ACTIVE":
        raise BizError("账号已停用", 403)
    access = create_access_token(user.id, user.username)
    refresh = create_refresh_token(user.id, user.username)
    write_audit(db, "LOGIN", "sys_user", user.id, "登录", user.id, request.client.host if request.client else None)
    db.commit()
    return ok(
        {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "must_change_pwd": user.must_change_pwd,
            "username": user.username,
            "class_id": user.class_id,
        }
    )


@router.post("/refresh")
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise BizError("刷新令牌无效或已过期", 401)
    user = db.get(SysUser, int(payload["sub"]))
    if user is None:
        raise BizError("账号不存在", 401)
    access = create_access_token(user.id, user.username)
    refresh = create_refresh_token(user.id, user.username)
    return ok({"access_token": access, "refresh_token": refresh, "token_type": "bearer"})


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, user.password_hash):
        raise BizError("原密码错误", 400)
    user.password_hash = hash_password(body.new_password)
    user.must_change_pwd = False
    write_audit(db, "UPDATE", "sys_user", user.id, "修改密码", user.id, request.client.host if request.client else None)
    db.commit()
    return ok(None, message="密码修改成功")
