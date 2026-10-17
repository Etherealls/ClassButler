"""学期工具：学期列表生成、当前学期计算、可编辑判断。

学期格式：`{起始年}-{结束年}-{1|2}`，如 2024-2025-1 表示 2024~2025 学年的第一学期。
- 第 1 学期（秋季）：约 9 月 1 日 ~ 次年 2 月底
- 第 2 学期（春季）：约 3 月 1 日 ~ 当年 8 月 31 日
"""
from datetime import date, timedelta

TOTAL_SEMESTERS = 10  # 5 学年 * 2 学期


def _parse_semester(semester: str) -> tuple[int, int]:
    """解析 '2024-2025-1' -> (2024, 1)，返回 (起始年, 学期序号)"""
    try:
        parts = semester.split("-")
        year = int(parts[0])
        seq = int(parts[-1])
        return year, seq
    except (ValueError, IndexError):
        raise ValueError(f"无效的学期格式: {semester}")


def semester_to_label(semester: str) -> str:
    """'2024-2025-1' -> '2024-2025 学年第一学期'"""
    year, seq = _parse_semester(semester)
    return f"{year}-{year + 1} 学年{'第一学期' if seq == 1 else '第二学期'}"


def generate_semesters(start_semester: str) -> list[str]:
    """从 start_semester 开始向后生成 10 个学期（5 学年）"""
    year, seq = _parse_semester(start_semester)
    result = []
    for i in range(TOTAL_SEMESTERS):
        cur_year = year + (i + (seq - 1)) // 2
        cur_seq = 1 + (i + (seq - 1)) % 2
        result.append(f"{cur_year}-{cur_year + 1}-{cur_seq}")
    return result


def _semester_bounds(semester: str) -> tuple[date, date]:
    """返回某学期的 (开始日期, 结束日期)。结束日期为下一学期开始前一天。"""
    year, seq = _parse_semester(semester)
    if seq == 1:
        start = date(year, 9, 1)
        # 结束：次年 2 月底
        end = date(year + 1, 3, 1)
    else:
        start = date(year + 1, 3, 1)
        end = date(year + 1, 9, 1)
    # 结束日期是不包含的（下一学期开始日），实际周期为 [start, end)
    return start, end


def get_current_semester(semesters: list[str], today: date | None = None) -> str | None:
    """根据当前日期在给定学期列表中判断当前学期。

    学期周期为 [该学期开始, 下一学期开始前一天]。返回命中的学期，无命中返回 None。
    """
    today = today or date.today()
    for sem in semesters:
        start, end = _semester_bounds(sem)
        if start <= today < end:
            return sem
    return None


def get_editable_semester(semesters: list[str], today: date | None = None) -> str | None:
    """返回当前可编辑的学期（即当前学期）。

    仅当前学期可修改；当前学期之外的学期不可修改。若当前日期不在任何学期内则返回 None。
    """
    return get_current_semester(semesters, today)


def is_editable(semester: str, semesters: list[str], today: date | None = None) -> bool:
    """判断某个学期当前是否可编辑（仅当前学期可编辑）"""
    cur = get_current_semester(semesters, today)
    return cur is not None and cur == semester


def build_semester_info(start_semester: str | None, today: date | None = None) -> dict:
    """构建学期信息：学期列表 + 当前学期 + 各学期是否可编辑 + 起止日期"""
    today = today or date.today()
    if not start_semester:
        return {
            "start_semester": None,
            "semesters": [],
            "current_semester": None,
            "editable_semester": None,
        }
    semesters = generate_semesters(start_semester)
    current = get_current_semester(semesters, today)
    return {
        "start_semester": start_semester,
        "semesters": [
            {
                "value": s,
                "label": semester_to_label(s),
                "start": _semester_bounds(s)[0].isoformat(),
                "end": (_semester_bounds(s)[1] - timedelta(days=1)).isoformat(),
                "editable": s == current,
                "is_current": s == current,
            }
            for s in semesters
        ],
        "current_semester": current,
        "editable_semester": current,
    }
