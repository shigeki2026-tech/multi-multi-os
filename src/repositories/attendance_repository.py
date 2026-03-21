from sqlalchemy import delete, select

from src.models.entities import (
    AttendanceIgnoreTarget,
    AttendanceRuleSet,
    AttendanceRun,
    AttendanceRunRow,
    AttendanceShiftRule,
)


DEFAULT_RULE_SET_NAME = "Default JST Rules"
DEFAULT_SHIFT_RULES = [
    {"shift_code": "A", "start_time": "09:00", "end_time": "18:00", "rule_type": "work", "note": ""},
    {"shift_code": "A'", "start_time": "09:30", "end_time": "18:30", "rule_type": "work", "note": ""},
    {"shift_code": "C", "start_time": "09:00", "end_time": "13:00", "rule_type": "work", "note": ""},
    {"shift_code": "D", "start_time": "10:00", "end_time": "19:00", "rule_type": "work", "note": ""},
    {"shift_code": "D'", "start_time": "10:30", "end_time": "19:30", "rule_type": "work", "note": ""},
    {"shift_code": "F", "start_time": "12:00", "end_time": "21:00", "rule_type": "work", "note": ""},
    {"shift_code": "G", "start_time": "16:00", "end_time": "20:00", "rule_type": "work", "note": ""},
    {"shift_code": "V", "start_time": "17:00", "end_time": "21:00", "rule_type": "work", "note": ""},
    {"shift_code": "P", "start_time": "11:00", "end_time": "20:00", "rule_type": "work", "note": ""},
    {"shift_code": "\u4f11", "start_time": None, "end_time": None, "rule_type": "off", "note": "\u52e4\u52d9\u306a\u3057"},
    {"shift_code": "\u6709", "start_time": None, "end_time": None, "rule_type": "paid_leave", "note": "\u52e4\u52d9\u306a\u3057 / 8H\u51fa\u52e4\u6271\u3044"},
    {"shift_code": "\u6709\u4f11", "start_time": None, "end_time": None, "rule_type": "paid_leave", "note": "\u52e4\u52d9\u306a\u3057 / 8H\u51fa\u52e4\u6271\u3044"},
    {"shift_code": "RDB", "start_time": None, "end_time": None, "rule_type": "ignore", "note": "\u7167\u5408\u5bfe\u8c61\u5916"},
]


class AttendanceRepository:
    def __init__(self, session):
        self.session = session

    def ensure_default_rules(self):
        stmt = select(AttendanceRuleSet).where(AttendanceRuleSet.is_active.is_(True)).order_by(AttendanceRuleSet.rule_set_id)
        rule_set = self.session.scalar(stmt)
        if rule_set is None:
            rule_set = AttendanceRuleSet(rule_name=DEFAULT_RULE_SET_NAME, timezone_mode="JST", is_active=True)
            self.session.add(rule_set)
            self.session.flush()

        existing_rules = self.session.scalars(
            select(AttendanceShiftRule).where(AttendanceShiftRule.rule_set_id == rule_set.rule_set_id)
        ).all()
        if existing_rules:
            return rule_set

        for rule in DEFAULT_SHIFT_RULES:
            self.session.add(AttendanceShiftRule(rule_set_id=rule_set.rule_set_id, **rule))
        self.session.flush()
        return rule_set

    def list_active_shift_rules(self):
        rule_set = self.ensure_default_rules()
        stmt = (
            select(AttendanceShiftRule)
            .where(AttendanceShiftRule.rule_set_id == rule_set.rule_set_id)
            .order_by(AttendanceShiftRule.shift_code)
        )
        return self.session.scalars(stmt).all()

    def list_active_ignore_targets(self):
        stmt = select(AttendanceIgnoreTarget).where(AttendanceIgnoreTarget.is_active.is_(True)).order_by(AttendanceIgnoreTarget.ignore_id)
        return self.session.scalars(stmt).all()

    def create_run(self, attendance_run: AttendanceRun):
        self.session.add(attendance_run)
        self.session.flush()
        return attendance_run

    def replace_run_rows(self, run_id: int, rows: list[AttendanceRunRow]):
        self.session.execute(delete(AttendanceRunRow).where(AttendanceRunRow.run_id == run_id))
        self.session.add_all(rows)
        self.session.flush()

    def list_recent_runs(self, limit: int = 10):
        stmt = select(AttendanceRun).order_by(AttendanceRun.executed_at.desc(), AttendanceRun.run_id.desc()).limit(limit)
        return self.session.scalars(stmt).all()
