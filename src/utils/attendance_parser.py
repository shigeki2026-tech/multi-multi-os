import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from io import BytesIO

import pandas as pd


EXCLUDED_POSTS = {"AM", "SV"}
SHIFT_DIRECT_PATTERN = re.compile(r"^\s*(\d{1,2})(?::?(\d{2}))?\s*[-~]\s*(\d{1,2})(?::?(\d{2}))?\s*$")

SHIFT_COLUMN_CANDIDATES = {
    "work_date": ["\u65e5\u4ed8", "\u52e4\u52d9\u65e5", "\u5bfe\u8c61\u65e5", "date", "work_date"],
    "employee_code": ["id", "\u793e\u54e1id", "\u793e\u54e1\u30b3\u30fc\u30c9", "\u5f93\u696d\u54e1\u30b3\u30fc\u30c9", "employee_code", "code"],
    "employee_name": ["\u6c0f\u540d", "\u540d\u524d", "\u793e\u54e1\u540d", "\u5f93\u696d\u54e1\u540d", "name", "employee_name"],
    "team_name": ["team", "\u30c1\u30fc\u30e0", "\u6240\u5c5e", "\u6240\u5c5e\u30c1\u30fc\u30e0", "team_name"],
    "post_code": ["post", "\u5f79\u8077", "\u30dd\u30b9\u30c8", "post_code"],
    "shift_raw": ["\u30b7\u30d5\u30c8", "\u52e4\u52d9", "\u52e4\u52d9\u8a18\u53f7", "\u30b7\u30d5\u30c8\u5165\u529b", "shift", "shift_code"],
}

PUNCH_COLUMN_CANDIDATES = {
    "work_date": ["\u65e5\u4ed8", "\u52e4\u52d9\u65e5", "\u5bfe\u8c61\u65e5", "date", "work_date"],
    "employee_code": ["id", "\u793e\u54e1id", "\u793e\u54e1\u30b3\u30fc\u30c9", "\u5f93\u696d\u54e1\u30b3\u30fc\u30c9", "employee_code", "code"],
    "employee_name": ["\u6c0f\u540d", "\u540d\u524d", "\u793e\u54e1\u540d", "\u5f93\u696d\u54e1\u540d", "name", "employee_name"],
    "team_name": ["team", "\u30c1\u30fc\u30e0", "\u6240\u5c5e", "\u6240\u5c5e\u30c1\u30fc\u30e0", "team_name"],
    "post_code": ["post", "\u5f79\u8077", "\u30dd\u30b9\u30c8", "post_code"],
    "actual_start": ["\u958b\u59cb", "\u51fa\u52e4", "\u958b\u59cb\u6642\u523b", "start", "clock_in", "actual_start"],
    "actual_end": ["\u7d42\u4e86", "\u9000\u52e4", "\u7d42\u4e86\u6642\u523b", "end", "clock_out", "actual_end"],
}


@dataclass
class ParsedShift:
    raw_value: str
    rule_type: str
    scheduled_start: datetime | None
    scheduled_end: datetime | None
    display_text: str
    note: str = ""


@dataclass
class ParsedActual:
    actual_start: datetime | None
    actual_end: datetime | None
    display_text: str
    note: str = ""


def read_uploaded_table(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        raise ValueError("\u30d5\u30a1\u30a4\u30eb\u304c\u9078\u629e\u3055\u308c\u3066\u3044\u307e\u305b\u3093\u3002")

    filename = uploaded_file.name.lower()
    payload = uploaded_file.getvalue()
    buffer = BytesIO(payload)
    if filename.endswith(".csv"):
        for encoding in ("utf-8-sig", "cp932", "utf-8"):
            try:
                buffer.seek(0)
                return pd.read_csv(buffer, encoding=encoding)
            except UnicodeDecodeError:
                continue
        buffer.seek(0)
        return pd.read_csv(buffer)
    if filename.endswith((".xlsx", ".xlsm", ".xls")):
        buffer.seek(0)
        return pd.read_excel(buffer)
    raise ValueError("\u5bfe\u5fdc\u3057\u3066\u3044\u306a\u3044\u30d5\u30a1\u30a4\u30eb\u5f62\u5f0f\u3067\u3059\u3002CSV \u307e\u305f\u306f Excel \u3092\u4f7f\u7528\u3057\u3066\u304f\u3060\u3055\u3044\u3002")


def normalize_shift_frame(df: pd.DataFrame) -> pd.DataFrame:
    normalized = _normalize_table(df, SHIFT_COLUMN_CANDIDATES, ["work_date", "shift_raw"])
    normalized["work_date"] = pd.to_datetime(normalized["work_date"], errors="coerce").dt.date
    for column in ("employee_code", "employee_name", "team_name", "post_code", "shift_raw"):
        normalized[column] = normalized[column].map(_clean_text)
    return normalized.dropna(subset=["work_date"]).reset_index(drop=True)


def normalize_punch_frame(df: pd.DataFrame) -> pd.DataFrame:
    normalized = _normalize_table(df, PUNCH_COLUMN_CANDIDATES, ["work_date", "actual_start", "actual_end"])
    normalized["work_date"] = pd.to_datetime(normalized["work_date"], errors="coerce").dt.date
    for column in ("employee_code", "employee_name", "team_name", "post_code", "actual_start", "actual_end"):
        normalized[column] = normalized[column].map(_clean_text)
    return normalized.dropna(subset=["work_date"]).reset_index(drop=True)


def build_rule_lookup(rules) -> dict[str, dict]:
    return {
        str(rule.shift_code).strip().upper(): {
            "start_time": rule.start_time,
            "end_time": rule.end_time,
            "rule_type": rule.rule_type,
            "note": rule.note or "",
        }
        for rule in rules
    }


def build_ignore_sets(ignore_targets) -> dict[str, set[str]]:
    return {
        "employee_codes": {str(item.employee_code).strip().upper() for item in ignore_targets if item.employee_code},
        "employee_names": {str(item.employee_name).strip() for item in ignore_targets if item.employee_name},
        "post_codes": {str(item.post_code).strip().upper() for item in ignore_targets if item.post_code},
    }


def parse_shift_row(work_date: date, shift_raw: str | None, rule_lookup: dict[str, dict]) -> ParsedShift:
    raw = _clean_text(shift_raw) or ""
    if not raw:
        return ParsedShift("", "empty", None, None, "-")

    lookup_key = raw.upper()
    if lookup_key in rule_lookup:
        rule = rule_lookup[lookup_key]
        if rule["rule_type"] in {"off", "paid_leave", "ignore"}:
            return ParsedShift(raw, rule["rule_type"], None, None, _display_for_nonwork(raw, rule["rule_type"]), rule["note"])
        start_dt = combine_date_and_hhmm(work_date, rule["start_time"])
        end_dt = combine_date_and_hhmm(work_date, rule["end_time"])
        if start_dt and end_dt and end_dt <= start_dt:
            end_dt += timedelta(days=1)
        return ParsedShift(raw, "work", start_dt, end_dt, f"{format_clock(start_dt)}-{format_clock(end_dt)}", rule["note"])

    match = SHIFT_DIRECT_PATTERN.match(raw)
    if match:
        start_dt = combine_date_and_parts(work_date, match.group(1), match.group(2))
        end_dt = combine_date_and_parts(work_date, match.group(3), match.group(4))
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        return ParsedShift(raw, "work", start_dt, end_dt, f"{format_clock(start_dt)}-{format_clock(end_dt)}", "\u76f4\u66f8\u304d\u30b7\u30d5\u30c8")

    return ParsedShift(raw, "unknown", None, None, raw, "\u52e4\u52d9\u8a18\u53f7\u3092\u89e3\u91c8\u3067\u304d\u307e\u305b\u3093")


def parse_actual_row(work_date: date, actual_start: str | None, actual_end: str | None) -> ParsedActual:
    start_dt = parse_clock_value(work_date, actual_start)
    end_dt = parse_clock_value(work_date, actual_end)
    if start_dt:
        start_dt = round_to_30_minutes(start_dt)
    if end_dt:
        end_dt = round_to_30_minutes(end_dt)
    if start_dt and end_dt and end_dt < start_dt:
        end_dt += timedelta(days=1)

    if start_dt and end_dt:
        return ParsedActual(start_dt, end_dt, f"{format_clock(start_dt)}-{format_clock(end_dt)}")
    if not actual_start and not actual_end:
        return ParsedActual(None, None, "-")
    return ParsedActual(start_dt, end_dt, "-", "\u958b\u59cb\u307e\u305f\u306f\u7d42\u4e86\u306e\u3069\u3061\u3089\u304b\u304c\u6b20\u843d\u3057\u3066\u3044\u307e\u3059")


def parse_clock_value(work_date: date, value) -> datetime | None:
    text = _clean_text(value)
    if not text:
        return None

    parsed = pd.to_datetime(text, errors="coerce")
    if pd.notna(parsed):
        if isinstance(parsed, pd.Timestamp):
            if parsed.year == 1970 and parsed.month == 1 and parsed.day == 1:
                return datetime.combine(work_date, parsed.time())
            return parsed.to_pydatetime()

    match = re.match(r"^\s*(\d{1,2})(?::?(\d{2}))?\s*$", text)
    if not match:
        return None
    return combine_date_and_parts(work_date, match.group(1), match.group(2))


def combine_date_and_hhmm(work_date: date, value: str | None) -> datetime | None:
    if not value:
        return None
    hour_text, minute_text = value.split(":")
    return datetime.combine(work_date, time(hour=int(hour_text), minute=int(minute_text)))


def combine_date_and_parts(work_date: date, hour_text: str, minute_text: str | None) -> datetime:
    return datetime.combine(work_date, time(hour=int(hour_text), minute=int(minute_text or 0)))


def round_to_30_minutes(value: datetime) -> datetime:
    discard = timedelta(minutes=value.minute % 30, seconds=value.second, microseconds=value.microsecond)
    rounded = value - discard
    if discard >= timedelta(minutes=15):
        rounded += timedelta(minutes=30)
    return rounded


def diff_minutes(later: datetime | None, earlier: datetime | None) -> int:
    if not later or not earlier:
        return 0
    return max(int((later - earlier).total_seconds() // 60), 0)


def format_duration(minutes: int | None) -> str:
    if not minutes:
        return "-"
    hours, remain = divmod(int(minutes), 60)
    return f"{hours}:{remain:02d}"


def format_clock(value: datetime | None) -> str:
    return value.strftime("%H:%M") if value else "-"


def format_display_date(value: date | None) -> str:
    return value.strftime("%Y-%m-%d") if value else "-"


def make_join_key(work_date: date, employee_code: str | None, employee_name: str | None) -> tuple:
    return (work_date, (employee_code or "").strip().upper(), (employee_name or "").strip())


def is_excluded_post(post_code: str | None) -> bool:
    return bool(post_code and post_code.strip().upper() in EXCLUDED_POSTS)


def match_ignore_target(employee_code: str | None, employee_name: str | None, post_code: str | None, ignore_sets: dict[str, set[str]]) -> bool:
    normalized_code = (employee_code or "").strip().upper()
    normalized_name = (employee_name or "").strip()
    normalized_post = (post_code or "").strip().upper()
    return (
        normalized_code in ignore_sets["employee_codes"]
        or normalized_name in ignore_sets["employee_names"]
        or normalized_post in ignore_sets["post_codes"]
    )


def to_export_bytes(summary_rows: list[dict], issue_rows: list[dict], settings_rows: list[dict]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="summary", index=False)
        pd.DataFrame(issue_rows).to_excel(writer, sheet_name="issue_details", index=False)
        pd.DataFrame(settings_rows).to_excel(writer, sheet_name="settings", index=False)
    output.seek(0)
    return output.read()


def to_csv_bytes(rows: list[dict]) -> bytes:
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")


def _normalize_table(df: pd.DataFrame, candidates: dict[str, list[str]], required_fields: list[str]) -> pd.DataFrame:
    renamed = {}
    normalized_columns = {_normalize_header(column): column for column in df.columns}
    for target, labels in candidates.items():
        match = _find_column(normalized_columns, labels)
        if match:
            renamed[match] = target
    standardized = df.rename(columns=renamed).copy()
    for field in required_fields:
        if field not in standardized.columns:
            raise ValueError(f"\u5fc5\u9808\u5217 `{field}` \u3092\u5224\u5b9a\u3067\u304d\u307e\u305b\u3093\u3067\u3057\u305f\u3002")
    for optional in candidates:
        if optional not in standardized.columns:
            standardized[optional] = None
    return standardized


def _normalize_header(value) -> str:
    return re.sub(r"[\s_\-/\uFF08\uFF09()]+", "", str(value).strip().lower())


def _find_column(normalized_columns: dict[str, str], labels: list[str]) -> str | None:
    normalized_labels = [_normalize_header(label) for label in labels]
    for label in normalized_labels:
        if label in normalized_columns:
            return normalized_columns[label]
    for normalized_name, original in normalized_columns.items():
        if any(label in normalized_name for label in normalized_labels):
            return original
    return None


def _clean_text(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _display_for_nonwork(raw: str, rule_type: str) -> str:
    if rule_type == "paid_leave":
        return f"{raw} (\u52e4\u52d9\u306a\u3057 / 8:00\u6271\u3044)"
    if rule_type == "off":
        return f"{raw} (\u52e4\u52d9\u306a\u3057)"
    if rule_type == "ignore":
        return f"{raw} (\u7121\u8996)"
    return raw
