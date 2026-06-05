"""応答率エンジン用マスタ（除外番号・放棄閾値・合算定義・OP）の管理サービス。

削除は行わず is_active=false（Operatorは status）で無効化するのを基本とする。
"""
from src.models.entities import AbandonRule, ExcludeNumber, Operator, SkillGroupMerge


class AnswerRateMasterService:
    def __init__(self, answer_rate_master_repository, audit_service=None):
        self.repo = answer_rate_master_repository
        self.audit_service = audit_service

    def _audit(self, table, record_id, action, actor_id, after=None):
        if self.audit_service:
            self.audit_service.log(table, record_id, action, actor_id, after=after)

    # --- exclude_numbers ---
    def list_exclude_numbers(self):
        return [
            {"id": x.id, "caller_number": x.caller_number, "reason": x.reason or "", "is_active": x.is_active}
            for x in self.repo.list_exclude_numbers(active_only=False)
        ]

    def create_exclude_number(self, actor_id: int, caller_number: str, reason: str):
        obj = ExcludeNumber(caller_number=caller_number.strip(), reason=reason.strip() or None, is_active=True)
        self.repo.add(obj)
        self._audit("exclude_numbers", obj.id, "create", actor_id, after=obj)
        return obj

    def toggle_exclude_number(self, actor_id: int, id_: int):
        obj = self.repo.get_exclude_number(id_)
        if obj:
            obj.is_active = not obj.is_active
            self.repo.add(obj)
            self._audit("exclude_numbers", obj.id, "update", actor_id, after=obj)
        return obj

    # --- abandon_rules ---
    def list_abandon_rules(self):
        return [
            {
                "id": r.id,
                "skill_group": r.skill_group or "(全体既定)",
                "threshold_seconds": r.threshold_seconds,
                "is_active": r.is_active,
            }
            for r in self.repo.list_abandon_rules(active_only=False)
        ]

    def create_abandon_rule(self, actor_id: int, skill_group: str | None, threshold_seconds: int):
        sg = (skill_group or "").strip() or None
        obj = AbandonRule(skill_group=sg, threshold_seconds=int(threshold_seconds), is_active=True)
        self.repo.add(obj)
        self._audit("abandon_rules", obj.id, "create", actor_id, after=obj)
        return obj

    def update_abandon_rule(self, actor_id: int, id_: int, threshold_seconds: int):
        obj = self.repo.get_abandon_rule(id_)
        if obj:
            obj.threshold_seconds = int(threshold_seconds)
            self.repo.add(obj)
            self._audit("abandon_rules", obj.id, "update", actor_id, after=obj)
        return obj

    def toggle_abandon_rule(self, actor_id: int, id_: int):
        obj = self.repo.get_abandon_rule(id_)
        if obj:
            obj.is_active = not obj.is_active
            self.repo.add(obj)
            self._audit("abandon_rules", obj.id, "update", actor_id, after=obj)
        return obj

    # --- skill_group_merge ---
    def list_skill_group_merge(self):
        return [
            {
                "id": m.id,
                "merge_label": m.merge_label,
                "child_skill_group": m.child_skill_group,
                "is_active": m.is_active,
            }
            for m in self.repo.list_skill_group_merge(active_only=False)
        ]

    def create_skill_group_merge(self, actor_id: int, merge_label: str, child_skill_group: str):
        obj = SkillGroupMerge(
            merge_label=merge_label.strip(),
            child_skill_group=child_skill_group.strip(),
            is_active=True,
        )
        self.repo.add(obj)
        self._audit("skill_group_merge", obj.id, "create", actor_id, after=obj)
        return obj

    def toggle_skill_group_merge(self, actor_id: int, id_: int):
        obj = self.repo.get_skill_group_merge(id_)
        if obj:
            obj.is_active = not obj.is_active
            self.repo.add(obj)
            self._audit("skill_group_merge", obj.id, "update", actor_id, after=obj)
        return obj

    # --- operators ---
    def list_operators(self):
        return [
            {
                "id": o.id,
                "op_code": o.op_code,
                "display_name": o.display_name,
                "skill_group": o.skill_group or "",
                "status": o.status,
                "shift_type": o.shift_type or "",
            }
            for o in self.repo.list_operators(active_only=False)
        ]

    def create_operator(self, actor_id: int, op_code: str, display_name: str, skill_group: str, shift_type: str):
        if self.repo.get_operator_by_code(op_code.strip()):
            raise ValueError("同じ op_code のオペレーターが既に存在します。")
        obj = Operator(
            op_code=op_code.strip(),
            display_name=display_name.strip(),
            skill_group=(skill_group or "").strip() or None,
            status="active",
            shift_type=(shift_type or "").strip() or None,
        )
        self.repo.add(obj)
        self._audit("operators", obj.id, "create", actor_id, after=obj)
        return obj

    def toggle_operator(self, actor_id: int, id_: int):
        obj = self.repo.get_operator(id_)
        if obj:
            obj.status = "inactive" if obj.status == "active" else "active"
            self.repo.add(obj)
            self._audit("operators", obj.id, "update", actor_id, after=obj)
        return obj
