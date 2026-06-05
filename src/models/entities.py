from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Team(TimestampMixin, Base):
    __tablename__ = "teams"

    team_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_name: Mapped[str] = mapped_column(String(255))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    google_email: Mapped[str | None] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    role: Mapped[str] = mapped_column(String(100))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.team_id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    project_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_name: Mapped[str] = mapped_column(String(255))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.team_id"))
    color: Mapped[str] = mapped_column(String(20), default="#4F8CFF")
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    requester_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    assignee_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.team_id"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.project_id"))
    priority: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    due_date: Mapped[date | None] = mapped_column(Date)
    requested_date: Mapped[date | None] = mapped_column(Date)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    related_link: Mapped[str | None] = mapped_column(Text)
    needs_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    deleted_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))

    comments: Mapped[list["TaskComment"]] = relationship(back_populates="task")


class TaskComment(Base):
    __tablename__ = "task_comments"

    comment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.task_id"))
    comment_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    comment_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped["Task"] = relationship(back_populates="comments")


class TaskWatcher(Base):
    __tablename__ = "task_watchers"

    watcher_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.task_id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RecurringTaskRule(TimestampMixin, Base):
    __tablename__ = "recurring_task_rules"

    rule_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    assignee_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    frequency_type: Mapped[str] = mapped_column(String(50))
    rule_expression: Mapped[str] = mapped_column(String(255))
    next_run_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CalendarSyncSetting(TimestampMixin, Base):
    __tablename__ = "calendar_sync_settings"

    sync_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    calendar_id: Mapped[str | None] = mapped_column(String(255))
    sync_mode: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)


class AppRegistry(TimestampMixin, Base):
    __tablename__ = "app_registry"

    app_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_key: Mapped[str] = mapped_column(String(100), unique=True)
    app_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class AppRunLog(Base):
    __tablename__ = "app_run_logs"

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_id: Mapped[int] = mapped_column(ForeignKey("app_registry.app_id"))
    executed_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50))
    message: Mapped[str | None] = mapped_column(Text)
    output_summary_json: Mapped[dict | None] = mapped_column(JSON)


class LeocSnapshot(Base):
    __tablename__ = "leoc_snapshots"

    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_time: Mapped[str] = mapped_column(String(20))
    inbound_count: Mapped[int] = mapped_column(Integer)
    lost_count: Mapped[int] = mapped_column(Integer)
    answer_rate: Mapped[float] = mapped_column(Numeric(5, 1))
    ai_count: Mapped[int] = mapped_column(Integer)
    form_count: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(50))
    source_ref: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReportJob(TimestampMixin, Base):
    __tablename__ = "report_jobs"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String(50))
    target_date: Mapped[date | None] = mapped_column(Date)
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    preview_text: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    sent_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    send_status: Mapped[str] = mapped_column(String(50))


class CallDetailJob(TimestampMixin, Base):
    __tablename__ = "call_detail_jobs"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    input_source: Mapped[str | None] = mapped_column(String(255))
    filter_json: Mapped[dict | None] = mapped_column(JSON)
    output_path: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    executed_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(100))
    record_id: Mapped[str] = mapped_column(String(100))
    action_type: Mapped[str] = mapped_column(String(50))
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)


class AttendanceRuleSet(TimestampMixin, Base):
    __tablename__ = "attendance_rule_sets"

    rule_set_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_name: Mapped[str] = mapped_column(String(255))
    timezone_mode: Mapped[str] = mapped_column(String(50), default="JST")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AttendanceShiftRule(TimestampMixin, Base):
    __tablename__ = "attendance_shift_rules"

    rule_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_set_id: Mapped[int] = mapped_column(ForeignKey("attendance_rule_sets.rule_set_id"))
    shift_code: Mapped[str] = mapped_column(String(50))
    start_time: Mapped[str | None] = mapped_column(String(10))
    end_time: Mapped[str | None] = mapped_column(String(10))
    rule_type: Mapped[str] = mapped_column(String(50), default="work")
    note: Mapped[str | None] = mapped_column(Text)


class AttendanceIgnoreTarget(TimestampMixin, Base):
    __tablename__ = "attendance_ignore_targets"

    ignore_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_code: Mapped[str | None] = mapped_column(String(100))
    employee_name: Mapped[str | None] = mapped_column(String(255))
    post_code: Mapped[str | None] = mapped_column(String(100))
    reason: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AttendanceRun(Base):
    __tablename__ = "attendance_runs"

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_label: Mapped[str | None] = mapped_column(String(255))
    shift_filename: Mapped[str | None] = mapped_column(String(255))
    punch_filename: Mapped[str | None] = mapped_column(String(255))
    executed_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    summary_json: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="completed")


class AttendanceRunRow(Base):
    __tablename__ = "attendance_run_rows"

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("attendance_runs.run_id"))
    work_date: Mapped[date | None] = mapped_column(Date)
    employee_code: Mapped[str | None] = mapped_column(String(100))
    employee_name: Mapped[str | None] = mapped_column(String(255))
    team_name: Mapped[str | None] = mapped_column(String(255))
    post_code: Mapped[str | None] = mapped_column(String(100))
    shift_raw: Mapped[str | None] = mapped_column(String(100))
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime)
    scheduled_end: Mapped[datetime | None] = mapped_column(DateTime)
    actual_start: Mapped[datetime | None] = mapped_column(DateTime)
    actual_end: Mapped[datetime | None] = mapped_column(DateTime)
    late_minutes: Mapped[int | None] = mapped_column(Integer)
    early_leave_minutes: Mapped[int | None] = mapped_column(Integer)
    overtime_minutes: Mapped[int | None] = mapped_column(Integer)
    result_type: Mapped[str | None] = mapped_column(String(100))
    result_note: Mapped[str | None] = mapped_column(Text)


# ---------------------------------------------------------------------------
# Phase 1: 応答率エンジン関連
# 注意: Operator はアプリ利用者(User)とは別物。OP/オペレーターを表す。
# ---------------------------------------------------------------------------


class Operator(TimestampMixin, Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    op_code: Mapped[str] = mapped_column(String(100), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    skill_group: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="active")
    shift_type: Mapped[str | None] = mapped_column(String(50))


class ExcludeNumber(TimestampMixin, Base):
    """テストコール等を応答率集計から除外する発信者番号マスタ。"""

    __tablename__ = "exclude_numbers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    caller_number: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AbandonRule(TimestampMixin, Base):
    """放棄呼の秒数閾値。skill_group が NULL の行は全体既定、指定行はスキルグループ別上書き。"""

    __tablename__ = "abandon_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_group: Mapped[str | None] = mapped_column(String(255))
    threshold_seconds: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SkillGroupMerge(TimestampMixin, Base):
    """合算定義。merge_label(親ラベル) ← child_skill_group(子グループ) を複数行で表現。"""

    __tablename__ = "skill_group_merge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merge_label: Mapped[str] = mapped_column(String(255))
    child_skill_group: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CallStat(TimestampMixin, Base):
    """CDR取込の集計値。raw skill_group の値のみ保存する（合算結果は保存しない）。"""

    __tablename__ = "call_stats"
    __table_args__ = (
        UniqueConstraint("stat_date", "time_slot", "skill_group", name="uq_call_stats_date_slot_group"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stat_date: Mapped[date] = mapped_column(Date)
    time_slot: Mapped[int] = mapped_column(Integer)  # 着信時間の「時」(0-23)
    skill_group: Mapped[str] = mapped_column(String(255))
    completed_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_abandon_count: Mapped[int] = mapped_column(Integer, default=0)


class ImportLog(Base):
    """CDR取込監査。後から数字を再現できるよう、取込時点のルールスナップショットを保存する。"""

    __tablename__ = "import_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255))
    encoding: Mapped[str | None] = mapped_column(String(50))
    row_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50))  # completed / failed
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    engine_version: Mapped[str | None] = mapped_column(String(50))
    threshold_rule_snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    exclude_numbers_snapshot_hash: Mapped[str | None] = mapped_column(String(64))
    definition_note: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
