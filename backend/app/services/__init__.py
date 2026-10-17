"""首启初始化：建表 + 创建默认班主任账号 + 默认班级"""
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import ClassInfo, SysUser


def init_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 创建默认班主任账号
        if db.query(SysUser).count() == 0:
            db.add(
                SysUser(
                    username=settings.default_username,
                    password_hash=hash_password(settings.default_password),
                    must_change_pwd=True,
                    status="ACTIVE",
                )
            )
            db.commit()
        # 创建默认班级（若无）
        if db.query(ClassInfo).count() == 0:
            db.add(ClassInfo(class_name="默认班级", grade_year=datetime_now_year()))
            db.commit()
        # 确保班主任账号绑定班级（若未绑定则绑定第一个班级）
        user = db.query(SysUser).first()
        cls = db.query(ClassInfo).first()
        if user and cls and user.class_id is None:
            user.class_id = cls.id
            db.commit()
    finally:
        db.close()


def datetime_now_year() -> int:
    from datetime import datetime

    return datetime.now().year


def ensure_user_bound_class(db: Session):
    """确保班主任账号绑定班级（若未绑定则绑定第一个班级）"""
    user = db.query(SysUser).first()
    cls = db.query(ClassInfo).first()
    if user and cls and user.class_id is None:
        user.class_id = cls.id
        db.commit()
