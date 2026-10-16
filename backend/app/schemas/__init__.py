"""Pydantic 请求/响应模型"""
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------- 认证 ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=64)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    must_change_pwd: bool = False


# ---------- 班级 ----------
class ClassInfoCreate(BaseModel):
    class_name: str
    grade_year: int
    major: Optional[str] = None


# ---------- 学生档案 ----------
class FamilyContactIn(BaseModel):
    parent_name: str
    relation: str
    phone: Optional[str] = None
    live_together: bool = True
    economy_level: str = "一般"


class StudentCreate(BaseModel):
    student_no: str
    name: str
    gender: str
    birth_date: Optional[date] = None
    id_card: Optional[str] = None
    nation: Optional[str] = None
    political: Optional[str] = None
    native_place: Optional[str] = None
    origin: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None
    emergency_name: Optional[str] = None
    emergency_phone: Optional[str] = None
    family_note: Optional[str] = None
    class_id: Optional[int] = None
    family_contacts: list[FamilyContactIn] = []


class StudentUpdate(BaseModel):
    student_no: Optional[str] = None
    name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    id_card: Optional[str] = None
    nation: Optional[str] = None
    political: Optional[str] = None
    native_place: Optional[str] = None
    origin: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None
    emergency_name: Optional[str] = None
    emergency_phone: Optional[str] = None
    family_note: Optional[str] = None
    class_id: Optional[int] = None


# ---------- 考勤 ----------
class AttendanceBatchRequest(BaseModel):
    class_id: Optional[int] = None
    att_date: date
    session: str
    # student_id -> status 映射；未列出的学生默认 NORMAL
    records: dict[int, str] = {}
    remark: Optional[str] = None


# ---------- 请假 ----------
class LeaveCreate(BaseModel):
    student_id: int
    leave_type: str
    start_time: datetime
    end_time: datetime
    duration_hours: float
    destination: Optional[str] = None
    reason: str
    attachment_url: Optional[str] = None
    note: Optional[str] = None


class LeaveUpdate(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None
    end_time: Optional[datetime] = None


# ---------- 查寝 ----------
class DormCheckBatchRequest(BaseModel):
    check_date: date
    # student_id -> status 映射
    records: dict[int, str] = {}
    remark: Optional[str] = None


# ---------- 纪律 ----------
class DisciplineCreate(BaseModel):
    student_id: int
    category: str
    occur_time: datetime
    location: Optional[str] = None
    fact: str
    result: Optional[str] = None


# ---------- 课程 / 成绩 ----------
class CourseCreate(BaseModel):
    course_name: str
    semester: str
    credit: float = 1.0


class ScoreUpdate(BaseModel):
    score: float


# ---------- 补考 ----------
class MakeupCreate(BaseModel):
    student_id: int
    course_id: int
    stage: str = "WAIT_MAKEUP"
    exam_time: Optional[datetime] = None
    result_score: Optional[float] = None
    note: Optional[str] = None


class MakeupUpdate(BaseModel):
    stage: Optional[str] = None
    exam_time: Optional[datetime] = None
    result_score: Optional[float] = None
    note: Optional[str] = None


# ---------- 荣誉 ----------
class AwardCreate(BaseModel):
    student_id: int
    event_name: str
    level: str
    award: str
    award_time: Optional[date] = None
    cert_no: Optional[str] = None


class CertificateCreate(BaseModel):
    student_id: int
    cert_name: str
    grade: Optional[str] = None
    obtain_time: Optional[date] = None
    cert_no: Optional[str] = None
    file_url: Optional[str] = None


# ---------- 组织 ----------
class CadreCreate(BaseModel):
    student_id: int
    position: str
    start_date: date
    end_date: Optional[date] = None


class DormAssignCreate(BaseModel):
    student_id: int
    room_no: str
    bed_no: str
    start_date: Optional[date] = None


class SeatPlanSave(BaseModel):
    rows: int
    cols: int
    layout: dict[str, Any]


class DutyScheduleCreate(BaseModel):
    weekday: int
    student_ids: list[int]
    note: Optional[str] = None


# ---------- 账号 ----------
class AccountUpdate(BaseModel):
    phone: Optional[str] = None
