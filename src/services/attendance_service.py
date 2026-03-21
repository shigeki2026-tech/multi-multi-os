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


LABEL_DATE = "\u65e5\u4ed8"
LABEL_NAME = "\u6c0f\u540d"
LABEL_SHIFT_RAW = "\u30b7\u30d5\u30c8\u5165\u529b"
LABEL_EXPECTED = "\u671f\u5f85\u52e4\u52d9\u6642\u9593"
LABEL_ACTUAL = "\u5b9f\u7e3e\u52e4\u52d9\u6642\u9593"
LABEL_LATE = "\u9045\u523b"
LABEL_EARLY = "\u65e9\u9000"
LABEL_OVERTIME = "\u6b8b\u696d"
LABEL_RESULT = "\u5224\u5b9a"
LABEL_NOTE = "\u5099\u8003"
STATUS_EXCLUDED = "\u9664\u5916"
STATUS_MATCH = "\u4e00\u81f4"
STATUS_MISSING = "\u52e4\u52d9\u4e88\u5b9a\u3060\u304c\u5b9f\u7e3e\u306a\u3057"
STATUS_REVIEW = "\u8981\u78ba\u8a8d"
STATUS_UNEXPECTED = "\u4f11\u307f\u30fb\u6709\u7d66\u3060\u304c\u5b9f\u7e3e\u3042\u308a"
SUMMARY_LATE = "\u9045\u523b\u4ef6\u6570"
SUMMARY_EARLY = "\u65e9\u9000\u4ef6\u6570"
SUMMARY_OVERTIME = "\u6b8b\u696d\u4ef6\u6570"
SUMMARY_MISSING = "\u52e4\u52d9\u4e88\u5b9a\u3060\u304c\u5b9f\u7e3e\u306a\u3057\u4ef6\u6570"
SUMMARY_UNEXPECTED = "\u4f11\u307f\u30fb\u6709\u7d66\u3060\u304c\u5b9f\u7e3e\u3042\u308a\u4ef6\u6570"
SUMMARY_REVIEW = "\u8981\u78ba\u8a8d\u4ef6\u6570"
SUMMARY_ISSUES = "\u5dee\u7570\u7dcf\u4ef6\u6570"
SUMMARY_TOTAL = "\u5168\u4ef6\u6570"


class AttendanceService:
    def __init__(self, attendance_repository, audit_service):
        self.attendance_repository = attendance_repository
        self.audit_service = audit_service

    def run_reconciliation(self, actor_id: int | None, target_label: str, punch_file, shift_file=None, shift_text: str = "", shift_input_mode: str = "file"):
        shift_filename = shift_file.name if shift_file is not None else "pasted_shift.tsv"
        shift_context_hint = " ".join(part for part in [target_label, shift_filename] if part)

        if shift_input_mode == "paste":
            shift_raw_df = read_pasted_shift_text(shift_text)
        else:
            shift_raw_df = read_uploaded_shift_table(shift_file)

        shift_df = normalize_shift_frame(prepare_shift_dataframe(shift_raw_df, context_hint=shift_context_hint))
        punch_df = normalize_punch_frame(read_uploaded_table(punch_file))
        if shift_df.empty:
            raise ValueError("\u30b7\u30d5\u30c8\u30d5\u30a1\u30a4\u30eb\u306b\u6709\u52b9\u306a\u30c7\u30fc\u30bf\u304c\u3042\u308a\u307e\u305b\u3093\u3002")
        if punch_df.empty:
            raise ValueError("\u6253\u523b\u30d5\u30a1\u30a4\u30eb\u306b\u6709\u52b9\u306a\u30c7\u30fc\u30bf\u304c\u3042\u308a\u307e\u305b\u3093\u3002")

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
                excluded_reasons.append(f"Post {post_code} \u306f\u9664\u5916\u5bfe\u8c61")
            if match_ignore_target(employee_code, employee_name, post_code, ignore_sets):
                excluded_reasons.append("\u7ba1\u7406\u753b\u9762\u306e\u9664\u5916\u5bfe\u8c61")
            if parsed_shift.rule_type == "ignore":
                excluded_reasons.append(f"\u52e4\u52d9\u8a18\u53f7 {parsed_shift.raw_value} \u306f\u7121\u8996\u8a2d\u5b9a")

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
        settings_rows = [{"\u533a\u5206": "\u57fa\u672c\u8a2d\u5b9a", "\u30ad\u30fc": "timezone_mode", "\u5024": "JST", "\u88dc\u8db3": "\u7167\u5408\u57fa\u6e96"}]
        for rule in rules:
            settings_rows.append(
                {
                    "\u533a\u5206": "\u52e4\u52d9\u8a18\u53f7",
                    "\u30ad\u30fc": rule.shift_code,
                    "\u5024": f"{rule.start_time or '-'}-{rule.end_time or '-'}",
                    "\u88dc\u8db3": f"{rule.rule_type} {rule.note or ''}".strip(),
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
