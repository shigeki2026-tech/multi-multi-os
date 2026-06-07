from datetime import date

from sqlalchemy import delete, func, select

from src.models.entities import AnswerRateThresholdStat


class AnswerRateThresholdRepository:
    """閲覧用中間集計 answer_rate_threshold_stats の保存・集計・削除。

    UI層へSQLAlchemy ORMオブジェクトを渡さない（dict/数値で返す）。
    合算値は保存しない。閲覧時は completed_count / valid_abandon_count の合計を返し、
    応答率は呼び出し側（answer_rate_service.answer_rate）で都度計算する。
    """

    def __init__(self, session):
        self.session = session

    # ------------------------------------------------------------------
    # 保存（取込時）
    # ------------------------------------------------------------------
    def bulk_insert(self, rows: list[dict], source_filename: str | None = None) -> int:
        objs = [
            AnswerRateThresholdStat(
                stat_date=r["stat_date"],
                time_slot=r["time_slot"],
                skill_group=r["skill_group"],
                threshold_seconds=r["threshold_seconds"],
                completed_count=r["completed_count"],
                valid_abandon_count=r["valid_abandon_count"],
                denominator=r["denominator"],
                answer_rate=r["answer_rate"],
                source_filename=source_filename,
            )
            for r in rows
        ]
        self.session.add_all(objs)
        self.session.flush()
        return len(objs)

    # ------------------------------------------------------------------
    # 閲覧（取込済みデータから・生CSV非走査）
    # ------------------------------------------------------------------
    def has_data(self) -> bool:
        return self.session.scalar(select(AnswerRateThresholdStat.id).limit(1)) is not None

    def stat_date_range(self) -> tuple[date | None, date | None]:
        row = self.session.execute(
            select(func.min(AnswerRateThresholdStat.stat_date),
                   func.max(AnswerRateThresholdStat.stat_date))
        ).one()
        return row[0], row[1]

    def list_skill_groups(self, start: date | None = None, end: date | None = None) -> list[str]:
        """期間内に存在する skill_group の一覧（昇順）。"""
        stmt = select(AnswerRateThresholdStat.skill_group).distinct()
        if start is not None:
            stmt = stmt.where(AnswerRateThresholdStat.stat_date >= start)
        if end is not None:
            stmt = stmt.where(AnswerRateThresholdStat.stat_date <= end)
        return sorted(str(x) for x in self.session.scalars(stmt).all())

    def aggregate_selected(self, start: date, end: date, skill_groups, threshold_seconds: int) -> dict:
        """選択回線群×指定閾値の合計（completed/valid_abandon）を返す。応答率は呼び出し側で計算。"""
        groups = [str(x) for x in skill_groups]
        if not groups:
            return {"completed_count": 0, "valid_abandon_count": 0}
        stmt = select(
            func.coalesce(func.sum(AnswerRateThresholdStat.completed_count), 0),
            func.coalesce(func.sum(AnswerRateThresholdStat.valid_abandon_count), 0),
        ).where(
            AnswerRateThresholdStat.stat_date >= start,
            AnswerRateThresholdStat.stat_date <= end,
            AnswerRateThresholdStat.threshold_seconds == int(threshold_seconds),
            AnswerRateThresholdStat.skill_group.in_(groups),
        )
        completed, valid_abandon = self.session.execute(stmt).one()
        return {"completed_count": int(completed), "valid_abandon_count": int(valid_abandon)}

    def compare_selected(self, start: date, end: date, skill_groups) -> list[dict]:
        """選択回線群について閾値ごとの合計を返す（閾値昇順）。応答率は呼び出し側で計算。"""
        groups = [str(x) for x in skill_groups]
        if not groups:
            return []
        stmt = (
            select(
                AnswerRateThresholdStat.threshold_seconds,
                func.coalesce(func.sum(AnswerRateThresholdStat.completed_count), 0),
                func.coalesce(func.sum(AnswerRateThresholdStat.valid_abandon_count), 0),
            )
            .where(
                AnswerRateThresholdStat.stat_date >= start,
                AnswerRateThresholdStat.stat_date <= end,
                AnswerRateThresholdStat.skill_group.in_(groups),
            )
            .group_by(AnswerRateThresholdStat.threshold_seconds)
            .order_by(AnswerRateThresholdStat.threshold_seconds)
        )
        return [
            {
                "threshold_seconds": int(t),
                "completed_count": int(c),
                "valid_abandon_count": int(va),
            }
            for t, c, va in self.session.execute(stmt).all()
        ]

    # ------------------------------------------------------------------
    # 削除（再取込用）
    # ------------------------------------------------------------------
    def count_in_range(self, start: date, end: date) -> int:
        stmt = select(func.count(AnswerRateThresholdStat.id)).where(
            AnswerRateThresholdStat.stat_date >= start,
            AnswerRateThresholdStat.stat_date <= end,
        )
        return int(self.session.scalar(stmt) or 0)

    def delete_in_range(self, start: date, end: date) -> int:
        result = self.session.execute(
            delete(AnswerRateThresholdStat).where(
                AnswerRateThresholdStat.stat_date >= start,
                AnswerRateThresholdStat.stat_date <= end,
            )
        )
        self.session.flush()
        return int(result.rowcount or 0)
