from sqlalchemy import select

from src.models.entities import AbandonRule, ExcludeNumber, Operator, SkillGroupMerge


class AnswerRateMasterRepository:
    """応答率エンジンが参照する4マスタ（除外番号・放棄閾値・合算定義・OP）のCRUD。"""

    def __init__(self, session):
        self.session = session

    # --- exclude_numbers ---
    def list_exclude_numbers(self, active_only: bool = False) -> list[ExcludeNumber]:
        stmt = select(ExcludeNumber)
        if active_only:
            stmt = stmt.where(ExcludeNumber.is_active.is_(True))
        return list(self.session.scalars(stmt.order_by(ExcludeNumber.id)).all())

    def get_exclude_number(self, id_: int) -> ExcludeNumber | None:
        return self.session.get(ExcludeNumber, id_)

    def add(self, obj):
        self.session.add(obj)
        self.session.flush()
        return obj

    # --- abandon_rules ---
    def list_abandon_rules(self, active_only: bool = False) -> list[AbandonRule]:
        stmt = select(AbandonRule)
        if active_only:
            stmt = stmt.where(AbandonRule.is_active.is_(True))
        return list(self.session.scalars(stmt.order_by(AbandonRule.id)).all())

    def get_abandon_rule(self, id_: int) -> AbandonRule | None:
        return self.session.get(AbandonRule, id_)

    # --- skill_group_merge ---
    def list_skill_group_merge(self, active_only: bool = False) -> list[SkillGroupMerge]:
        stmt = select(SkillGroupMerge)
        if active_only:
            stmt = stmt.where(SkillGroupMerge.is_active.is_(True))
        return list(self.session.scalars(stmt.order_by(SkillGroupMerge.merge_label, SkillGroupMerge.id)).all())

    def get_skill_group_merge(self, id_: int) -> SkillGroupMerge | None:
        return self.session.get(SkillGroupMerge, id_)

    def list_skill_group_merge_by_label(self, merge_label: str, active_only: bool = False) -> list[SkillGroupMerge]:
        """指定 merge_label に紐づく行を返す（child_skill_group 昇順）。"""
        stmt = select(SkillGroupMerge).where(SkillGroupMerge.merge_label == merge_label)
        if active_only:
            stmt = stmt.where(SkillGroupMerge.is_active.is_(True))
        return list(self.session.scalars(stmt.order_by(SkillGroupMerge.child_skill_group)).all())

    def get_skill_group_merge_pair(self, merge_label: str, child_skill_group: str) -> SkillGroupMerge | None:
        """(merge_label, child_skill_group) の組に一致する1行を返す（無ければ None）。"""
        return self.session.scalar(
            select(SkillGroupMerge).where(
                SkillGroupMerge.merge_label == merge_label,
                SkillGroupMerge.child_skill_group == child_skill_group,
            )
        )

    # --- operators ---
    def list_operators(self, active_only: bool = False) -> list[Operator]:
        stmt = select(Operator)
        if active_only:
            stmt = stmt.where(Operator.status == "active")
        return list(self.session.scalars(stmt.order_by(Operator.op_code)).all())

    def get_operator(self, id_: int) -> Operator | None:
        return self.session.get(Operator, id_)

    def get_operator_by_code(self, op_code: str) -> Operator | None:
        return self.session.scalar(select(Operator).where(Operator.op_code == op_code))
