from datetime import date

from sqlalchemy import func, select

from src.models.entities import CallStat, ImportLog


class CallStatsRepository:
    def __init__(self, session):
        self.session = session

    def exists_for_keys(self, keys: list[tuple]) -> list[tuple]:
        """(stat_date, time_slot, skill_group) のうち、既にcall_statsに存在するキーを返す。

        同一期間・同一スキルグループの二重取込をDBのユニーク制約で拒否する前に、
        プレビュー段階で衝突を検知するために使う。
        """
        existing = []
        for stat_date, time_slot, skill_group in keys:
            stmt = select(CallStat.id).where(
                CallStat.stat_date == stat_date,
                CallStat.time_slot == time_slot,
                CallStat.skill_group == skill_group,
            )
            if self.session.scalar(stmt) is not None:
                existing.append((stat_date, time_slot, skill_group))
        return existing

    def bulk_insert_stats(self, stats: list[dict]) -> int:
        objs = [
            CallStat(
                stat_date=s["stat_date"],
                time_slot=s["time_slot"],
                skill_group=s["skill_group"],
                completed_count=s["completed_count"],
                valid_abandon_count=s["valid_abandon_count"],
            )
            for s in stats
        ]
        self.session.add_all(objs)
        self.session.flush()
        return len(objs)

    def list_stats(self, start: date | None = None, end: date | None = None) -> list[CallStat]:
        stmt = select(CallStat)
        if start is not None:
            stmt = stmt.where(CallStat.stat_date >= start)
        if end is not None:
            stmt = stmt.where(CallStat.stat_date <= end)
        stmt = stmt.order_by(CallStat.stat_date, CallStat.time_slot, CallStat.skill_group)
        return list(self.session.scalars(stmt).all())

    def latest_stat_date(self):
        return self.session.scalar(select(func.max(CallStat.stat_date)))

    def count_stats(self) -> int:
        """call_stats の総行数。二重取込検出時に既存件数を画面表示するために使う。"""
        return int(self.session.scalar(select(func.count(CallStat.id))) or 0)

    def create_import_log(self, log: ImportLog) -> ImportLog:
        self.session.add(log)
        self.session.flush()
        return log

    def list_import_logs(self, limit: int = 50) -> list[ImportLog]:
        stmt = select(ImportLog).order_by(ImportLog.imported_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def latest_import_logs(self, limit: int = 50) -> list[dict]:
        """import_log を「セッション内で属性を読み切った plain dict のリスト」で返す。

        UI層へSQLAlchemy ORMオブジェクトを渡さない。ImportLogはrepository層でdict化する。
        （ORMをUIに渡すとセッション終了後の属性アクセスで DetachedInstanceError になるため。）
        """
        logs = self.list_import_logs(limit=limit)
        return [
            {
                "id": lg.id,
                "filename": lg.filename,
                "encoding": lg.encoding,
                "row_count": lg.row_count,
                "status": lg.status,
                "engine_version": lg.engine_version,
                "imported_at": str(lg.imported_at) if lg.imported_at is not None else "",
                "error": lg.error_message or "",
            }
            for lg in logs
        ]
