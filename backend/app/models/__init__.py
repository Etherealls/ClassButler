"""数据模型：基础档案与组织（M1）、登录账号"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SysUser(Base, TimestampMixin):
    """登录账号（仅班主任单账号）"""

    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    class_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    must_change_pwd: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")


class ClassInfo(Base, TimestampMixin):
    __tablename__ = "class_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_name: Mapped[str] = mapped_column(String(64), nullable=False)
    grade_year: Mapped[int] = mapped_column(Integer, nullable=False)
    major: Mapped[str | None] = mapped_column(String(64), nullable=True)
    head_teacher_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    students: Mapped[list["StudentProfile"]] = relationship(
        back_populates="class_info", lazy="selectin"
    )


class StudentProfile(Base, TimestampMixin):
    __tablename__ = "student_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_no: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    gender: Mapped[str] = mapped_column(String(4), nullable=False)  # 男/女
    birth_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    id_card: Mapped[str | None] = mapped_column(String(18), nullable=True)
    nation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    political: Mapped[str | None] = mapped_column(String(16), nullable=True)
    native_place: Mapped[str | None] = mapped_column(String(64), nullable=True)
    origin: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    emergency_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    emergency_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    family_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    class_id: Mapped[int] = mapped_column(Integer, ForeignKey("class_info.id"), nullable=False)

    class_info: Mapped["ClassInfo"] = relationship(back_populates="students", lazy="selectin")
    family_contacts: Mapped[list["FamilyContact"]] = relationship(
        back_populates="student", lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("class_id", "student_no", name="uk_class_studentno"),)


class FamilyContact(Base, TimestampMixin):
    __tablename__ = "family_contact"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("student_profile.id"))
    parent_name: Mapped[str] = mapped_column(String(32), nullable=False)
    relation: Mapped[str] = mapped_column(String(16), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    live_together: Mapped[bool] = mapped_column(Boolean, default=True)
    economy_level: Mapped[str] = mapped_column(String(16), default="一般")

    student: Mapped["StudentProfile"] = relationship(back_populates="family_contacts")


class ClassCadre(Base, TimestampMixin):
    __tablename__ = "class_cadre"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[str] = mapped_column(String(32), nullable=False)
    start_date: Mapped[str] = mapped_column(Date, nullable=False)
    end_date: Mapped[str | None] = mapped_column(Date, nullable=True)


class DutySchedule(Base, TimestampMixin):
    __tablename__ = "duty_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-7 周一~周日
    student_ids: Mapped[str] = mapped_column(Text, nullable=False)  # 逗号分隔学生id
    jobs: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: {student_id: 工作}
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)


class SeatPlan(Base, TimestampMixin):
    __tablename__ = "seat_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    rows: Mapped[int] = mapped_column(Integer, default=6)
    cols: Mapped[int] = mapped_column(Integer, default=8)
    layout: Mapped[str] = mapped_column(Text, nullable=False)  # JSON 字符串
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)


class DormRoom(Base, TimestampMixin):
    __tablename__ = "dorm_room"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_no: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=4)


class DormAssignment(Base, TimestampMixin):
    __tablename__ = "dorm_assignment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    room_no: Mapped[str] = mapped_column(String(16), nullable=False)
    bed_no: Mapped[str | None] = mapped_column(String(8), nullable=True)
    start_date: Mapped[str] = mapped_column(Date, nullable=True)
    end_date: Mapped[str | None] = mapped_column(Date, nullable=True)


class Course(Base, TimestampMixin):
    __tablename__ = "course"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_name: Mapped[str] = mapped_column(String(64), nullable=False)
    semester: Mapped[str] = mapped_column(String(16), nullable=False)
    credit: Mapped[float] = mapped_column(default=1.0)


class ScoreRecord(Base, TimestampMixin):
    __tablename__ = "score_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[str] = mapped_column(String(16), nullable=False)
    score: Mapped[float | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "semester", name="uk_stu_course_sem"),
    )


class CompetitionAward(Base, TimestampMixin):
    __tablename__ = "competition_award"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)  # 校/市/省/国家/国际
    award: Mapped[str] = mapped_column(String(64), nullable=False)
    award_time: Mapped[str] = mapped_column(Date, nullable=True)
    cert_no: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Certificate(Base, TimestampMixin):
    __tablename__ = "certificate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cert_name: Mapped[str] = mapped_column(String(128), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(32), nullable=True)
    obtain_time: Mapped[str] = mapped_column(Date, nullable=True)
    cert_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(255), nullable=True)


class SysAuditLog(Base):
    __tablename__ = "sys_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operator_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    target_table: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class QualityEvaluation(Base, TimestampMixin):
    """综合素质评价（德育/智育/体育/美育/劳育）"""

    __tablename__ = "quality_evaluation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[str] = mapped_column(String(16), nullable=False)
    level: Mapped[str] = mapped_column(String(8), nullable=False)  # 优秀/良好/合格/不合格
    moral: Mapped[int] = mapped_column(Integer, nullable=False, default=0)    # 德育
    intellect: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 智育
    sport: Mapped[int] = mapped_column(Integer, nullable=False, default=0)    # 体育
    art: Mapped[int] = mapped_column(Integer, nullable=False, default=0)     # 美育
    labor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)   # 劳育
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)   # 合计
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 班级排名
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "semester", name="uk_stu_quality_sem"),
    )
