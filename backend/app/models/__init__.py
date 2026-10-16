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
    student_ids: Mapped[str] = mapped_column(Text, nullable=False)  # 逗号分隔学号/学生id
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
    bed_no: Mapped[str] = mapped_column(String(8), nullable=False)
    start_date: Mapped[str] = mapped_column(Date, nullable=True)
    end_date: Mapped[str | None] = mapped_column(Date, nullable=True)


class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    class_id: Mapped[int] = mapped_column(Integer, nullable=False)
    att_date: Mapped[str] = mapped_column(Date, nullable=False)
    session: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recorder_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "att_date", "session", name="uk_day_session"),
    )


class LeaveRequest(Base, TimestampMixin):
    __tablename__ = "leave_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    leave_type: Mapped[str] = mapped_column(String(16), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_hours: Mapped[float] = mapped_column(nullable=False)
    destination: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="LEAVING")
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)


class DormCheck(Base, TimestampMixin):
    __tablename__ = "dorm_check"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    room_no: Mapped[str] = mapped_column(String(16), nullable=False)
    check_date: Mapped[str] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checker_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DisciplineRecord(Base, TimestampMixin):
    __tablename__ = "discipline_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    occur_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fact: Mapped[str] = mapped_column(String(500), nullable=False)
    result: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recorder_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


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


class MakeupTrack(Base, TimestampMixin):
    __tablename__ = "makeup_track"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(24), nullable=False)
    exam_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    result_score: Mapped[float | None] = mapped_column(nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)


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
