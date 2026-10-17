"""教学安排接口：课程表（班级/班主任）、实训课程表、校历"""
import json
import re
from io import BytesIO

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, write_audit
from app.core.response import BizError, ok
from app.models import CalendarEvent, ScheduleEntry, ScheduleSetting, SysUser
from app.schemas import CalendarEventSave, ScheduleEntrySave, ScheduleSettingSave
from app.utils import export_rows_to_xlsx, parse_xlsx

router = APIRouter(tags=["教学安排"])

# 课程表类型
SCHEDULE_TYPES = {"class": "班级课程表", "teacher": "班主任课程表", "training": "实训课程表"}
# 校历类型
CALENDAR_TYPES = {"class": "上课", "holiday": "假期", "exam": "考试"}

DEFAULT_PERIODS = [
    "08:00-08:45", "08:55-09:40", "10:00-10:45", "10:55-11:40",  # 上午
    "14:00-14:45", "14:55-15:40", "16:00-16:45", "16:55-17:40",  # 下午
]


def _serialize_setting(s: ScheduleSetting) -> dict:
    periods = json.loads(s.periods) if s.periods else []
    total = s.morning_count + s.afternoon_count
    if len(periods) != total:
        # 节数或时间段不一致时，用默认时间段补齐
        periods = (periods + DEFAULT_PERIODS)[:total]
    return {
        "id": s.id,
        "type": s.type,
        "type_label": SCHEDULE_TYPES.get(s.type, s.type),
        "semester": s.semester,
        "morning_count": s.morning_count,
        "afternoon_count": s.afternoon_count,
        "total_count": total,
        "periods": periods,
    }


def _get_or_create_setting(db: Session, type_: str, semester: str) -> ScheduleSetting:
    s = db.query(ScheduleSetting).filter(
        ScheduleSetting.type == type_, ScheduleSetting.semester == semester
    ).first()
    if s is None:
        s = ScheduleSetting(type=type_, semester=semester)
        db.add(s)
        db.flush()
    return s


# ---------- 课程表设置 ----------
@router.get("/schedule/settings")
def list_settings(
    semester: str | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回各类型课程表设置（不含具体课程，课程用 /schedule/entries 拉取）"""
    q = db.query(ScheduleSetting)
    if semester:
        q = q.filter(ScheduleSetting.semester == semester)
    items = q.order_by(ScheduleSetting.semester.desc()).all()
    return ok([_serialize_setting(s) for s in items])


@router.get("/schedule/setting")
def get_setting(
    type: str = Query(...),
    semester: str = Query(...),
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取某类型某学期的课程表设置（不存在则返回默认配置，不落库）"""
    s = db.query(ScheduleSetting).filter(
        ScheduleSetting.type == type, ScheduleSetting.semester == semester
    ).first()
    if s is None:
        return ok(
            {
                "id": None,
                "type": type,
                "type_label": SCHEDULE_TYPES.get(type, type),
                "semester": semester,
                "morning_count": 4,
                "afternoon_count": 4,
                "total_count": 8,
                "periods": DEFAULT_PERIODS[:8],
            }
        )
    return ok(_serialize_setting(s))


@router.post("/schedule/setting")
def save_setting(
    body: ScheduleSettingSave,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """保存课程表设置（节数、时间段）"""
    if body.type not in SCHEDULE_TYPES:
        raise BizError("无效的课程表类型", 400)
    if not (1 <= body.morning_count <= 12) or not (1 <= body.afternoon_count <= 12):
        raise BizError("节数需在 1~12 之间", 400)
    s = db.query(ScheduleSetting).filter(
        ScheduleSetting.type == body.type, ScheduleSetting.semester == body.semester
    ).first()
    is_new = s is None
    if is_new:
        s = ScheduleSetting(type=body.type, semester=body.semester)
        db.add(s)
    s.morning_count = body.morning_count
    s.afternoon_count = body.afternoon_count
    total = body.morning_count + body.afternoon_count
    periods = body.periods or []
    if len(periods) != total:
        periods = (periods + DEFAULT_PERIODS)[:total]
    s.periods = json.dumps(periods, ensure_ascii=False)
    write_audit(db, "UPDATE", "schedule_setting", s.id,
                f"保存{SCHEDULE_TYPES[body.type]}设置({body.semester})", user.id,
                request.client.host if request.client else None)
    db.commit()
    db.refresh(s)
    return ok(_serialize_setting(s), message="课程表设置已保存")


# ---------- 课程安排 ----------
@router.get("/schedule/entries")
def list_entries(
    setting_id: int = Query(...),
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取某课程表的全部课程单元格"""
    setting = db.get(ScheduleSetting, setting_id)
    if setting is None:
        raise BizError("课程表设置不存在", 404)
    entries = db.query(ScheduleEntry).filter(
        ScheduleEntry.setting_id == setting_id
    ).all()
    return ok(
        [
            {
                "id": e.id,
                "weekday": e.weekday,
                "period_index": e.period_index,
                "course_name": e.course_name,
                "teacher_name": e.teacher_name,
                "location": e.location,
            }
            for e in entries
        ]
    )


@router.post("/schedule/entry")
def save_entry(
    body: ScheduleEntrySave,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """保存/更新单个课程单元格（upsert）"""
    setting = db.get(ScheduleSetting, body.setting_id)
    if setting is None:
        raise BizError("课程表设置不存在", 404)
    if not (1 <= body.weekday <= 7):
        raise BizError("星期需在 1~7 之间", 400)
    total = setting.morning_count + setting.afternoon_count
    if not (0 <= body.period_index < total):
        raise BizError("节次超出范围", 400)
    e = db.query(ScheduleEntry).filter(
        ScheduleEntry.setting_id == body.setting_id,
        ScheduleEntry.weekday == body.weekday,
        ScheduleEntry.period_index == body.period_index,
    ).first()
    if e is None:
        e = ScheduleEntry(
            setting_id=body.setting_id,
            weekday=body.weekday,
            period_index=body.period_index,
        )
        db.add(e)
    e.course_name = body.course_name
    e.teacher_name = body.teacher_name
    e.location = body.location
    db.commit()
    db.refresh(e)
    return ok({"id": e.id}, message="已保存")


@router.delete("/schedule/entry/{entry_id}")
def delete_entry(
    entry_id: int,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除某课程单元格"""
    e = db.get(ScheduleEntry, entry_id)
    if e:
        db.delete(e)
        db.commit()
    return ok(None, message="已删除")


# ---------- 课程表导入 ----------
def _read_schedule_xlsx(content: bytes) -> list[tuple[int, tuple]]:
    """读取 xlsx 原始行，返回 [(行号(1起), 值元组)]，跳过全空行"""
    from openpyxl import load_workbook

    wb = load_workbook(BytesIO(content), read_only=True)
    ws = wb.active
    out: list[tuple[int, tuple]] = []
    for row_no, r in enumerate(ws.iter_rows(values_only=True), start=1):
        if all(v is None or str(v).strip() == "" for v in r):
            continue
        out.append((row_no, tuple(r)))
    return out


def _parse_weeks(text: str) -> list[int]:
    """解析周次文本，如 '1-7(单),8,12' / '2-6(双),9,11' / '9-16' -> [1,3,5,7,8,12]"""
    weeks: list[int] = []
    for token in re.split(r"[,，]", str(text).strip()):
        token = token.strip()
        if not token:
            continue
        m = re.match(r"^(\d+)\s*-\s*(\d+)(?:\((单|双)\))?$", token)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            parity = m.group(3)
            for w in range(a, b + 1):
                if parity == "单" and w % 2 == 0:
                    continue
                if parity == "双" and w % 2 == 1:
                    continue
                weeks.append(w)
        elif re.match(r"^\d+$", token):
            weeks.append(int(token))
    return weeks


def _parse_periods(text: str) -> list[int]:
    """解析节次文本，如 '1-4' / '1' / '1,3,5' -> [1,2,3,4] / [1] / [1,3,5]（返回从 0 起的索引）"""
    idxs: list[int] = []
    for token in re.split(r"[,，]", str(text).strip()):
        token = token.strip()
        if not token:
            continue
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", token)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a > b:
                a, b = b, a
            idxs.extend(range(a - 1, b))
        elif re.match(r"^\d+$", token):
            idxs.append(int(token) - 1)
    return sorted(set(i for i in idxs if i >= 0))


@router.get("/schedule/import-template")
def download_import_template(_=Depends(get_current_user)):
    """下载课程表导入模板（数据从第 3 行开始）"""
    import io

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "排课数据"
    ws["A1"] = "说明：数据从第3行开始导入，*为必填项（课程名称、周次、星期和节次）；周次支持 1-7(单),8,12 格式；星期 1-7；节次支持 1 或 1-4 格式，多个以英文逗号分隔；以星期+节次为主键，重复数据覆盖。"
    headers = ["课程代码", "*课程名称", "教师工号", "教师姓名", "教学班编号", "教学班名称", "*周次", "*星期", "*节次", "上课地点"]
    for col, h in enumerate(headers, start=1):
        ws.cell(row=3, column=col, value=h)
    # 示例行
    sample = ["KCA", "课程A", "JSA", "教师A", "CRA", "班级A", "9-16", 5, "1-1", "文管楼a401"]
    for col, v in enumerate(sample, start=1):
        ws.cell(row=4, column=col, value=v)
    buf = io.BytesIO()
    wb.save(buf)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=schedule_import_template.xlsx"},
    )


@router.post("/schedule/import")
async def import_schedule(
    file: UploadFile = File(...),
    type: str = Query(...),
    semester: str = Query(...),
    request: Request = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导入排课数据（xlsx，数据从第 3 行开始），以「星期+节次」为主键，重复数据覆盖"""
    if type not in SCHEDULE_TYPES:
        raise BizError("无效的课程表类型", 400)
    content = await file.read()
    raw_rows = _read_schedule_xlsx(content)
    if not raw_rows:
        raise BizError("文件为空或格式错误", 400)

    # 表头行定位：查找包含「课程名称」「星期」「节次」的行（模板在第 3 行）
    header_row = None
    for row_no, values in raw_rows[:10]:
        joined = "|".join(str(v or "") for v in values)
        if "课程名称" in joined and "星期" in joined and "节次" in joined:
            header_row = (row_no, values)
            break
    if header_row is None:
        raise BizError("未找到表头行（需包含：课程名称、星期、节次）", 400)
    hdr_no, hdr_values = header_row
    headers = [str(v or "").strip().lstrip("*") for v in hdr_values]

    def col_of(*names: str) -> int | None:
        for n in names:
            for i, h in enumerate(headers):
                if h == n:
                    return i
        return None

    c_name = col_of("课程名称")
    c_teacher = col_of("教师姓名")
    c_week = col_of("周次")
    c_weekday = col_of("星期")
    c_period = col_of("节次")
    c_loc = col_of("上课地点")
    if c_name is None or c_week is None or c_weekday is None or c_period is None:
        raise BizError("缺少必填列（课程名称、周次、星期、节次）", 400)

    setting = _get_or_create_setting(db, type, semester)
    total = setting.morning_count + setting.afternoon_count

    success, skipped, errors = 0, 0, []
    for row_no, values in raw_rows:
        if row_no <= hdr_no:
            continue
        r = values

        def cell(ci: int | None) -> str:
            if ci is None or ci >= len(r):
                return ""
            return str(r[ci] or "").strip()

        name = cell(c_name)
        week_txt = cell(c_week)
        weekday_txt = cell(c_weekday)
        period_txt = cell(c_period)
        if not any([name, week_txt, weekday_txt, period_txt]):
            continue  # 空行跳过
        if not name:
            errors.append({"row": row_no, "reason": "课程名称为空"})
            continue
        if not weekday_txt.isdigit() or not (1 <= int(weekday_txt) <= 7):
            errors.append({"row": row_no, "reason": f"星期无效: {weekday_txt}"})
            continue
        weekday = int(weekday_txt)
        period_idxs = _parse_periods(period_txt)
        if not period_idxs:
            errors.append({"row": row_no, "reason": f"节次无效: {period_txt}"})
            continue
        teacher = cell(c_teacher)
        location = cell(c_loc)
        # 周次：超出当前节数配置的节次跳过
        for pi in period_idxs:
            if pi >= total:
                skipped += 1
                continue
            e = (
                db.query(ScheduleEntry)
                .filter(
                    ScheduleEntry.setting_id == setting.id,
                    ScheduleEntry.weekday == weekday,
                    ScheduleEntry.period_index == pi,
                )
                .first()
            )
            if e is None:
                e = ScheduleEntry(setting_id=setting.id, weekday=weekday, period_index=pi)
                db.add(e)
            e.course_name = name
            e.teacher_name = teacher
            e.location = location
            success += 1
    write_audit(db, "IMPORT", "schedule_entry", setting.id,
                f"导入{SCHEDULE_TYPES[type]} {success} 格", user.id,
                request.client.host if request.client else None)
    db.commit()
    msg = f"导入成功 {success} 格"
    if skipped:
        msg += f"，跳过 {skipped} 格（超出节数范围）"
    return ok({"success": success, "skipped": skipped, "errors": errors}, message=msg)


# ---------- 校历 ----------
@router.get("/calendar/events")
def list_calendar(
    start: str | None = None,
    end: str | None = None,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按日期范围查询校历事件"""
    q = db.query(CalendarEvent)
    if start:
        q = q.filter(CalendarEvent.date >= start)
    if end:
        q = q.filter(CalendarEvent.date <= end)
    items = q.order_by(CalendarEvent.date.asc()).all()
    return ok(
        [
            {
                "id": e.id,
                "date": e.date.isoformat(),
                "type": e.type,
                "type_label": CALENDAR_TYPES.get(e.type, e.type),
                "note": e.note,
            }
            for e in items
        ]
    )


@router.post("/calendar/event")
def save_calendar(
    body: CalendarEventSave,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """新增/更新校历事件（同一天同一类型覆盖）"""
    if body.type not in CALENDAR_TYPES:
        raise BizError("无效的校历类型", 400)
    e = db.query(CalendarEvent).filter(
        CalendarEvent.date == body.date, CalendarEvent.type == body.type
    ).first()
    is_new = e is None
    if is_new:
        e = CalendarEvent(date=body.date, type=body.type)
        db.add(e)
    e.note = body.note
    write_audit(db, "UPDATE", "calendar_event", e.id,
                f"{'新增' if is_new else '更新'}校历 {body.date} {CALENDAR_TYPES[body.type]}", user.id,
                request.client.host if request.client else None)
    db.commit()
    db.refresh(e)
    return ok({"id": e.id}, message="已保存")


@router.delete("/calendar/event/{event_id}")
def delete_calendar(
    event_id: int,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除校历事件"""
    e = db.get(CalendarEvent, event_id)
    if e:
        db.delete(e)
        db.commit()
    return ok(None, message="已删除")


# ---------- 校历图片导入 ----------
def _parse_calendar_image(content: bytes, semester: str | None = None) -> tuple[list[dict], list[str]]:
    """解析校历图片，返回 (事件列表, 警告列表)。

    识别规则：
    - 第一列为周次序号（忽略）；第一行为星期表头（一~日）
    - 灰色底纹方格 = 假期，白色底纹 = 上课
    - 「日/月」格式（如 1/9）更新当前月份，其后纯数字日期沿用该月份
    - 灰色方格第二行文字（如 中秋节）为假期名称，延续到后续灰格直到下一个白色格
    - 含「考试」文字的方格 = 考试
    - 日期按行优先（从左到右、从上到下）排列
    """
    import cv2
    import numpy as np

    from rapidocr_onnxruntime import RapidOCR

    img_data = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img_data is None:
        raise BizError("图片解码失败，请确认文件为有效图片", 400)
    # 放大图片以识别单字（一~日、单个数字在原图上常被漏检）
    scale = 2.5
    big = cv2.resize(img_data, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    ocr = RapidOCR(text_score=0.3)
    result, _ = ocr(big)
    if not result:
        raise BizError("图片中未识别到任何文字，请确认图片清晰", 400)

    items = []
    for box, text, conf in result:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        items.append({
            "text": str(text).strip(),
            "cx": sum(xs) / 4,
            "cy": sum(ys) / 4,
            "x1": min(xs), "x2": max(xs),
            "y1": min(ys), "y2": max(ys),
            "h": max(ys) - min(ys),
        })
    if not items:
        raise BizError("图片中未识别到任何文字", 400)

    # 1) 找表头行：包含 >=3 个单字星期（一~日）的条目
    wd_map = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
    header_items = []
    for it in items:
        t = it["text"].replace("星期", "").replace("礼拜", "")
        if t in wd_map:
            it2 = dict(it)
            it2["wd"] = wd_map[t]
            header_items.append(it2)
    if len(header_items) < 3:
        raise BizError("未识别到星期表头（一~日），请确认图片为校历表格", 400)
    # 表头行应位于图片顶部：取 y 最小的一组（彼此 y 接近的）
    header_items.sort(key=lambda h: h["cy"])
    base_y = header_items[0]["cy"]
    header_row = [h for h in header_items if h["cy"] - base_y < h["h"] * 3]
    if len(header_row) < 3:
        header_row = header_items
    header_row.sort(key=lambda h: h["cx"])

    # 列位置：优先用表格竖线检测，失败则用表头线性回归
    gray_img = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    H_px, W_px = bw.shape

    def _line_positions(mask, axis: int, min_ratio: float) -> list[int]:
        """检测直线位置：axis=1 找横线（按行求和），axis=0 找竖线"""
        proj = mask.mean(axis=axis) / 255.0
        idxs = np.where(proj > min_ratio)[0]
        lines: list[int] = []
        for i in idxs:
            if lines and i - lines[-1][-1] <= 3:
                lines[-1].append(int(i))
            else:
                lines.append([int(i)])
        return [int(np.mean(g)) for g in lines]

    horiz_mask = cv2.morphologyEx(
        bw, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, W_px // 12), 1)),
    )
    # 竖线常因抗锯齿存在缺口，先闭运算修补再提取
    bw_closed = cv2.morphologyEx(
        bw, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (3, 15)),
    )
    vert_mask = cv2.morphologyEx(
        bw_closed, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, H_px // 12))),
    )
    h_lines = _line_positions(horiz_mask, 1, 0.5)
    v_lines = _line_positions(vert_mask, 0, 0.5)

    use_lines = len(h_lines) >= 4 and len(v_lines) >= 4
    if use_lines:
        # 行边界 = 相邻横线之间；列边界 = 相邻竖线之间
        row_bands = [(h_lines[i], h_lines[i + 1]) for i in range(len(h_lines) - 1) if h_lines[i + 1] - h_lines[i] > 20]
        col_bands = [(v_lines[i], v_lines[i + 1]) for i in range(len(v_lines) - 1) if v_lines[i + 1] - v_lines[i] > 20]
        # 用表头文字定位星期列：找到包含各表头 cx 的列带
        header_band_wd: list[tuple[int, int]] = []  # (band_idx, wd)
        for h in header_row:
            for bi, (lo, hi) in enumerate(col_bands):
                if lo <= h["cx"] <= hi:
                    header_band_wd.append((bi, h["wd"]))
                    break
        if len(header_band_wd) >= 3:
            header_band_wd.sort()
            offset = header_band_wd[0][0] - header_band_wd[0][1]
            # 星期 wd -> 列带（bands 索引 = wd + offset）
            col_bounds = {}
            for wd in range(7):
                bi = wd + offset
                if 0 <= bi < len(col_bands):
                    lo, hi = col_bands[bi]
                    col_bounds[wd] = (float(lo), float(hi))
            # 周次列 = 星期列左侧最近的列带
            day_left = min(b[0] for b in col_bounds.values())
            week_band = [b for b in col_bands if b[1] <= day_left + 5]
            first_col_left = week_band[0][0] if week_band else 0.0
        else:
            use_lines = False

    if not use_lines:
        # 回退：表头线性回归 + 行聚类
        ws_known = np.array([h["wd"] for h in header_row], dtype=float)
        cxs_known = np.array([h["cx"] for h in header_row], dtype=float)
        if len(set(ws_known)) < 2:
            raise BizError("星期表头识别异常", 400)
        a_coef, b_coef = np.polyfit(ws_known, cxs_known, 1)
        avg_gap = abs(float(a_coef))
        col_bounds = {}
        for wd in range(7):
            cx = a_coef * wd + b_coef
            col_bounds[wd] = (cx - avg_gap / 2, cx + avg_gap / 2)
        first_col_left = col_bounds[0][0]
        # 行聚类：区间重叠法
        day_items_tmp = [it for it in items if it["cy"] > base_y + it["h"]]
        pad = avg_gap * 0.12
        expanded = sorted(((it["y1"] - pad, it["y2"] + pad, it) for it in day_items_tmp), key=lambda x: x[0])
        rows = []
        cur: list[dict] = []
        cur_end = -1.0
        for lo, hi, it in expanded:
            if cur and lo > cur_end:
                rows.append(cur)
                cur = []
                cur_end = -1.0
            cur.append(it)
            cur_end = max(cur_end, hi)
        if cur:
            rows.append(cur)
        row_bands = [
            (min(it["y1"] for it in r), max(it["y2"] for it in r)) for r in rows
        ]
    else:
        # 表头行以下的行带 = 数据行（表头带是包含最多表头文字的行带）
        header_band_idx = 0
        best = -1
        for bi, (lo, hi) in enumerate(row_bands):
            n = sum(1 for h in header_row if lo <= h["cy"] <= hi)
            if n > best:
                best = n
                header_band_idx = bi
        filtered = [b for b in row_bands if b[0] >= row_bands[header_band_idx][1] and b != row_bands[header_band_idx]]
        if filtered:
            row_bands = filtered
    if not row_bands:
        raise BizError("未识别到日期数据行", 400)
    row_bounds = row_bands

    # 2) 背景色采样（灰/白），使用放大后的图（与文字坐标同一坐标系）
    img = big
    avg_gap = sum(b[1] - b[0] for b in col_bounds.values()) / len(col_bounds)

    def is_gray_cell(wd: int, row_idx: int) -> bool:
        if wd not in col_bounds or row_idx >= len(row_bounds):
            return False
        left, right = col_bounds[wd]
        y_top, y_bot = row_bounds[row_idx]
        cx = int((left + right) / 2)
        cy = int((y_top + y_bot) / 2)
        size = max(4, int(min(right - left, y_bot - y_top) * 0.18))
        region = img[max(0, cy - size):cy + size, max(0, cx - size):cx + size]
        if region.size == 0:
            return False
        return float(region.mean()) < 215

    # 3) 组装网格：条目按 (行带, 列带) 归属；grid[row][weekday] = 按 y 排序的文字条目
    grid: list[dict[int, list]] = [dict() for _ in row_bounds]
    for it in items:
        # 行带归属
        ri = None
        for bi, (lo, hi) in enumerate(row_bounds):
            if lo <= it["cy"] <= hi:
                ri = bi
                break
        if ri is None:
            continue
        # 列归属
        if it["cx"] < first_col_left - avg_gap * 0.1:
            continue  # 周次列
        wd = None
        for w, (left, right) in col_bounds.items():
            if left <= it["cx"] <= right:
                wd = w
                break
        if wd is None:
            continue
        grid[ri].setdefault(wd, []).append(it)
    for ri in range(len(grid)):
        for wd in grid[ri]:
            grid[ri][wd].sort(key=lambda x: x["y1"])

    # 5) 年份：优先由学期参数推导（格式 YYYY-YYYY-N）
    year_pair: tuple[int, int] | None = None
    if semester:
        m = re.match(r"^(20\d{2})-(20\d{2})-(\d)$", semester)
        if m:
            year_pair = (int(m.group(1)), int(m.group(2)))
    if year_pair is None:
        for it in items:
            m = re.search(r"(20\d{2})\s*[-—~至]\s*(20\d{2})", it["text"])
            if m:
                year_pair = (int(m.group(1)), int(m.group(2)))
                break

    date_slash = re.compile(r"^(\d{1,2})\s*/\s*(\d{1,2})$")
    pure_num = re.compile(r"^(\d{1,2})$")
    slash_in = re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})")

    import datetime as _dt

    def year_for(month: int, seq: int | None) -> int:
        if year_pair:
            y1, y2 = year_pair
            if seq == 2:
                return y2
            return y1 if month >= 8 else y2
        today_y = _dt.date.today().year
        return today_y if month >= 8 else today_y + 1

    # 6) 逐格解析（行优先：从左到右、从上到下）
    events: list[dict] = []
    warnings: list[str] = []
    cur_month: int | None = None
    cur_holiday_name: str | None = None

    for ri in range(len(grid)):
        for wd in sorted(grid[ri].keys()):
            cells = grid[ri][wd]
            texts = [c["text"] for c in cells]
            joined = "".join(texts)
            gray = is_gray_cell(wd, ri)

            day: int | None = None
            month: int | None = None
            note_parts: list[str] = []
            for t in texts:
                m = date_slash.match(t)
                if m:
                    day, month = int(m.group(1)), int(m.group(2))
                    continue
                m = slash_in.search(t)
                if m and day is None:
                    day, month = int(m.group(1)), int(m.group(2))
                    note_parts.append(t)
                    continue
                m2 = pure_num.match(t)
                if m2 and day is None:
                    day = int(m2.group(1))
                    continue
                note_parts.append(t)

            if month is not None:
                cur_month = month
            note = "".join(note_parts).strip()

            if day is None:
                if "考试" in joined:
                    warnings.append(f"「{joined}」未对应具体日期，已忽略")
                continue
            if cur_month is None:
                warnings.append(f"日期 {day} 无法确定月份（需先出现「日/月」格式），已忽略")
                continue

            seq = int(semester.split("-")[-1]) if semester and re.match(r"^20\d{2}-20\d{2}-\d$", semester) else None
            try:
                d = _dt.date(year_for(cur_month, seq), cur_month, day)
            except ValueError:
                warnings.append(f"无效日期 {cur_month}/{day}，已忽略")
                continue

            if "考试" in joined:
                events.append({"date": d.isoformat(), "type": "exam", "note": note or joined})
                cur_holiday_name = None
            elif gray:
                name = note if note and not pure_num.match(note) else None
                if name:
                    cur_holiday_name = name
                events.append({"date": d.isoformat(), "type": "holiday", "note": name or cur_holiday_name or ""})
            else:
                cur_holiday_name = None
                events.append({"date": d.isoformat(), "type": "class", "note": note or ""})

    return events, warnings


@router.post("/calendar/import-image")
async def import_calendar_image(
    file: UploadFile = File(...),
    semester: str | None = Query(None),
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """导入校历图片：自动识别上课/假期/考试并写入校历"""
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png"):
        raise BizError("仅支持 JPG/PNG 图片", 400)
    content = await file.read()
    events, warnings = _parse_calendar_image(content, semester)
    if not events:
        raise BizError("未能从图片中识别出有效日期数据", 400)
    saved = 0
    for ev in events:
        e = db.query(CalendarEvent).filter(
            CalendarEvent.date == _parse_iso_date(ev["date"]),
            CalendarEvent.type == ev["type"],
        ).first()
        if e is None:
            e = CalendarEvent(date=_parse_iso_date(ev["date"]), type=ev["type"])
            db.add(e)
        e.note = ev["note"] or None
        saved += 1
    write_audit(db, "IMPORT", "calendar_event", None, f"导入校历图片 {saved} 天", user.id,
                request.client.host if request.client else None)
    db.commit()
    stats = {"class": sum(1 for e in events if e["type"] == "class"),
             "holiday": sum(1 for e in events if e["type"] == "holiday"),
             "exam": sum(1 for e in events if e["type"] == "exam")}
    return ok({"saved": saved, "stats": stats, "warnings": warnings[:10]},
              message=f"导入成功：上课 {stats['class']} 天、假期 {stats['holiday']} 天、考试 {stats['exam']} 天")


def _parse_iso_date(s: str):
    import datetime as _dt
    return _dt.date.fromisoformat(s)
