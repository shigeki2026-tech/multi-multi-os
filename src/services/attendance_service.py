from collections import Counter

from src.models.entities import AttendanceRun, AttendanceRunRow
from src.utils.attendance_parser import (
    build_ignore_sets,
    build_rule_lookup,
    diff_minutes,
    format_display_date,
    format_duration,
    is_excluded_post,
    make_join_key,
    match_ignore_target,
    normalize_punch_frame,
    normalize_shift_frame,
    parse_actual_row,
    parse_shift_row,
    prepare_shift_dataframe,
    read_pasted_shift_text,
    read_uploaded_shift_table,
    read_uploaded_table,
)


LABEL_DATE = "日付"
LABEL_NAME = "氏名"
LABEL_SHIFT_RAW = "シフト入力"
LABEL_EXPECTED = "期待勤務時間"
LABEL_ACTUAL = "実績勤務時間"
LABEL_LATE = "遅刻"
LABEL_EARLY = "早退"
LABEL_OVERTIME = "残業"
LABEL_RESULT = "判定"
LABEL_NOTE = "備考"
STATUS_EXCLUDED = "除外"
STATUS_MATCH = "一致"
STATUS_MISSING = "勤務予定だが実績なし"
STATUS_REVIEW = "要確認"
STATUS_UNEXPECTED = "休み・有給だが実績あり"
SUMMARY_LATE = "遅刻件数"
SUMMARY_EARLY = "早退件数"
SUMMARY_OVERTIME = "残業件数"
SUMMARY_MISSING = "勤務予定だが実績なし件数"
SUMMARY_UNEXPECTED = "休み・有給だが実績あり件数"
SUMMARY_REVIEW = "要確認件数"
SUMMARY_ISSUES = "差異総件数"
SUMMARY_TOTAL = "全件数"


class AttendanceService:
    def __init__(self, attendance_repository, audit_service):
        self.attendance_repository = attendance_repository
        self.audit_service = audit_service

    def run_reconciliation(
        self,
        actor_id: int | None,
        target_label: str,
        punch_file,
        shift_file=None,
        shift_text: str = "",
        shift_input_mode: str = "file",
    ):
        shift_filename = shift_file.name if shift_file is not None else "pasted_shift.tsv"
        shift_context_hint = " ".join(part for part in [target_label, shift_filename] if part)

        if shift_input_mode == "paste":
            shift_raw_df = read_pasted_shift_text(shift_text)
        else:
            shift_raw_df = read_uploaded_shift_table(shift_file)

        try:
            shift_prepared_df = prepare_shift_dataframe(shift_raw_df, context_hint=shift_context_hint)
            shift_df = normalize_shift_frame(shift_prepared_df)
        except Exception as exc:
            raise ValueError(f"シフト側エラー: {exc}")

        punch_raw_df = read_uploaded_table(punch_file)

        try:
            punch_df = normalize_punch_frame(punch_raw_df)
        except Exception as exc:
            raise ValueError(f"打刻CSV側エラー: {exc} / columns={list(punch_raw_df.columns)}")

        if shift_df.empty:
            raise ValueError("シフトファイルに有効なデータがありません。")
        if punch_df.empty:
            raise ValueError("打刻ファイルに有効なデータがありません。")

        rules = self.attendance_repository.list_active_shift_rules()
        ignore_targets = self.attendance_repository.list_active_ignore_targets()
        rule_lookup = build_rule_lookup(rules)
        ignore_sets = build_ignore_sets(ignore_targets)

        shift_rows = {
            make_join_key(row["work_date"], row["employee_code"], row["employee_name"]): row
            for row in shift_df.to_dict(orient="records")
        }
        punch_rows = {
            make_join_key(row["work_date"], row["employee_code"], row["employee_name"]): row
            for row in punch_df.to_dict(orient="records")
        }

        all_keys = sorted(set(shift_rows) | set(punch_rows), key=lambda item: (item[2], item[1], item[0]))
        counters = Counter()
        all_results = []
        issue_results = []
        issue_entities = []

        for key in all_keys:
            shift_row = shift_rows.get(key, {})
            punch_row = punch_rows.get(key, {})
            work_date = key[0]
            employee_code = shift_row.get("employee_code") or punch_row.get("employee_code")
            employee_name = shift_row.get("employee_name") or punch_row.get("employee_name")
            team_name = shift_row.get("team_name") or punch_row.get("team_name")
            post_code = shift_row.get("post_code") or punch_row.get("post_code")

            parsed_shift = parse_shift_row(work_date, shift_row.get("shift_raw"), rule_lookup)
            parsed_actual = parse_actual_row(work_date, punch_row.get("actual_start"), punch_row.get("actual_end"))

            excluded_reasons = []
            if is_excluded_post(post_code):
                excluded_reasons.append(f"Post {post_code} は除外対象")
            if match_ignore_target(employee_code, employee_name, post_code, ignore_sets):
                excluded_reasons.append("管理画面の除外対象")
            if parsed_shift.rule_type == "ignore":
                excluded_reasons.append(f"勤務記号 {parsed_shift.raw_value} は無視設定")

            late_minutes = 0
            early_leave_minutes = 0
            overtime_minutes = 0
            result_type = ""
            note_parts = [parsed_shift.note, parsed_actual.note]

            if excluded_reasons:
                result_type = STATUS_EXCLUDED
                note_parts.extend(excluded_reasons)
            elif parsed_shift.rule_type == "work":
                if not parsed_actual.actual_start and not parsed_actual.actual_end:
                    result_type = STATUS_MISSING
                elif not parsed_actual.actual_start or not parsed_actual.actual_end:
                    result_type = STATUS_REVIEW
                else:
                    late_minutes = diff_minutes(parsed_actual.actual_start, parsed_shift.scheduled_start)
                    early_leave_minutes = diff_minutes(parsed_shift.scheduled_end, parsed_actual.actual_end)
                    overtime_minutes = diff_minutes(parsed_actual.actual_end, parsed_shift.scheduled_end)
                    labels = []
                    if late_minutes > 0:
                        labels.append(LABEL_LATE)
                    if early_leave_minutes > 0:
                        labels.append(LABEL_EARLY)
                    if overtime_minutes > 0:
                        labels.append(LABEL_OVERTIME)
                    result_type = " / ".join(labels)
            elif parsed_shift.rule_type in {"off", "paid_leave"}:
                if parsed_actual.actual_start or parsed_actual.actual_end:
                    result_type = STATUS_UNEXPECTED
            elif parsed_shift.rule_type == "empty":
                if parsed_actual.actual_start or parsed_actual.actual_end:
                    result_type = STATUS_REVIEW
            else:
                result_type = STATUS_REVIEW

            issue_flag = bool(result_type and result_type != STATUS_EXCLUDED)
            if issue_flag:
                if late_minutes > 0:
                    counters["late_count"] += 1
                if early_leave_minutes > 0:
                    counters["early_leave_count"] += 1
                if overtime_minutes > 0:
                    counters["overtime_count"] += 1
                if result_type == STATUS_MISSING:
                    counters["missing_punch_count"] += 1
                if result_type == STATUS_UNEXPECTED:
                    counters["unexpected_work_count"] += 1
                if result_type == STATUS_REVIEW:
                    counters["review_count"] += 1

            row = {
                LABEL_DATE: format_display_date(work_date),
                "ID": employee_code or "-",
                LABEL_NAME: employee_name or "-",
                "Team": team_name or "-",
                "Post": post_code or "-",
                LABEL_SHIFT_RAW: parsed_shift.raw_value or "-",
                LABEL_EXPECTED: parsed_shift.display_text,
                LABEL_ACTUAL: parsed_actual.display_text,
                LABEL_LATE: format_duration(late_minutes),
                LABEL_EARLY: format_duration(early_leave_minutes),
                LABEL_OVERTIME: format_duration(overtime_minutes),
                LABEL_RESULT: result_type or STATUS_MATCH,
                LABEL_NOTE: " / ".join(part for part in note_parts if part) or "-",
                "_work_date": work_date,
                "_excluded": bool(excluded_reasons),
            }
            all_results.append(row)

            if issue_flag:
                issue_results.append({field: value for field, value in row.items() if not field.startswith("_")})
                issue_entities.append(
                    AttendanceRunRow(
                        work_date=work_date,
                        employee_code=employee_code,
                        employee_name=employee_name,
                        team_name=team_name,
                        post_code=post_code,
                        shift_raw=parsed_shift.raw_value or None,
                        scheduled_start=parsed_shift.scheduled_start,
                        scheduled_end=parsed_shift.scheduled_end,
                        actual_start=parsed_actual.actual_start,
                        actual_end=parsed_actual.actual_end,
                        late_minutes=late_minutes or None,
                        early_leave_minutes=early_leave_minutes or None,
                        overtime_minutes=overtime_minutes or None,
                        result_type=result_type,
                        result_note=" / ".join(part for part in note_parts if part) or None,
                    )
                )

        summary = {
            SUMMARY_LATE: counters["late_count"],
            SUMMARY_EARLY: counters["early_leave_count"],
            SUMMARY_OVERTIME: counters["overtime_count"],
            SUMMARY_MISSING: counters["missing_punch_count"],
            SUMMARY_UNEXPECTED: counters["unexpected_work_count"],
            SUMMARY_REVIEW: counters["review_count"],
            SUMMARY_ISSUES: len(issue_results),
            SUMMARY_TOTAL: len(all_results),
        }
        settings_rows = [{"区分": "基本設定", "キー": "timezone_mode", "値": "JST", "補足": "照合基準"}]
        for rule in rules:
            settings_rows.append(
                {
                    "区分": "勤務記号",
                    "キー": rule.shift_code,
                    "値": f"{rule.start_time or '-'}-{rule.end_time or '-'}",
                    "補足": f"{rule.rule_type} {rule.note or ''}".strip(),
                }
            )

        attendance_run = self.attendance_repository.create_run(
            AttendanceRun(
                target_label=target_label.strip() or None,
                shift_filename=shift_filename,
                punch_filename=punch_file.name,
                executed_by=actor_id,
                summary_json=summary,
                status="completed",
            )
        )
        for entity in issue_entities:
            entity.run_id = attendance_run.run_id
        self.attendance_repository.replace_run_rows(attendance_run.run_id, issue_entities)
        self.audit_service.log(
            table_name="attendance_runs",
            record_id=str(attendance_run.run_id),
            action_type="create",
            changed_by=actor_id,
            after={"run_id": attendance_run.run_id, "target_label": target_label, "summary": summary},
        )
        return {
            "run_id": attendance_run.run_id,
            "target_label": target_label,
            "summary": summary,
            "all_rows": all_results,
            "issue_rows": issue_results,
            "settings_rows": settings_rows,
        }

    def list_recent_runs_for_display(self, limit: int = 10):
        rows = []
        for run in self.attendance_repository.list_recent_runs(limit=limit):
            summary = run.summary_json or {}
            rows.append(
                {
                    "run_id": run.run_id,
                    "target_label": run.target_label or "-",
                    "executed_at": run.executed_at,
                    "shift_filename": run.shift_filename or "-",
                    "punch_filename": run.punch_filename or "-",
                    SUMMARY_ISSUES: summary.get(SUMMARY_ISSUES, 0),
                    SUMMARY_REVIEW: summary.get(SUMMARY_REVIEW, 0),
                    "status": run.status,
                }
            )
        return rows