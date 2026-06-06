from datetime import date

from src.services import answer_rate_service as ar


class DashboardService:
    def __init__(self, task_repository, request_repository, calendar_service, leoc_service, master_repository,
                 call_stats_repository=None):
        self.task_repository = task_repository
        self.request_repository = request_repository
        self.calendar_service = calendar_service
        self.leoc_service = leoc_service
        self.master_repository = master_repository
        self.call_stats_repository = call_stats_repository

    def get_answer_rate_dashboard_summary(self) -> dict:
        """ホーム画面の応答率サマリを「セッション内で集計済みの plain dict」として返す。

        ORM行（CallStat / ImportLog）の属性アクセスはすべてこのメソッド内（DBセッションが
        開いている間）で完了させる。UI層（app.py）へはORMを渡さず数値・文字列のみ返すことで
        DetachedInstanceError を防ぐ。応答率の計算定義は ar.answer_rate を変更せず利用する。
        """
        latest_date = self.call_stats_repository.latest_stat_date()
        rows = self.call_stats_repository.list_stats(latest_date, latest_date) if latest_date else []
        completed = sum(r.completed_count for r in rows)
        valid_abandon = sum(r.valid_abandon_count for r in rows)

        logs = self.call_stats_repository.list_import_logs(limit=1)
        log = logs[0] if logs else None
        return {
            "latest_date": str(latest_date) if latest_date else None,
            "completed_count": completed,
            "valid_abandon_count": valid_abandon,
            "answer_rate": ar.answer_rate(completed, valid_abandon) if rows else None,
            "group_count": len(rows),
            "has_data": bool(rows),
            "latest_import_id": log.id if log else None,
            "latest_import_filename": log.filename if log else None,
            "latest_import_status": log.status if log else None,
            "latest_import_at": str(log.imported_at) if log else None,
        }

    def get_dashboard_data(self, user_id: int):
        today_due = self.task_repository.list_today_due_tasks(user_id)
        overdue = self.task_repository.list_overdue_tasks(user_id)
        unack_requests = self.request_repository.list_received(user_id, only_unack=True)
        latest = self.leoc_service.latest_for_dashboard()
        today_events = self.calendar_service.get_todays_events(user_id)
        calendar_status = self.calendar_service.get_status()

        # TODO: recurring_task_rules の自動展開結果もここに統合する
        today_items = []
        today_items.extend(self._task_rows(today_due, label="今日期限タスク"))
        today_items.extend(self._task_rows(overdue, label="期限超過タスク"))
        today_items.extend(self._request_rows(unack_requests, label="未確認SV依頼"))

        overdue_items = self._task_rows(overdue, label="期限超過タスク")
        return {
            "today_count": len(today_items),
            "unack_requests": len(unack_requests),
            "overdue_count": len(overdue),
            "today_events": today_events,
            "calendar_status": calendar_status,
            "today_items": today_items,
            "overdue_items": overdue_items,
            "latest_leoc_rate": latest["answer_rate"] if latest else "-",
            "latest_leoc": latest,
        }

    def _name_map(self):
        return {user.user_id: user.display_name for user in self.master_repository.list_users()}

    def _task_rows(self, tasks, label: str):
        names = self._name_map()
        return [
            {
                "区分": label,
                "タイトル": task.title,
                "担当者": names.get(task.assignee_user_id, "-"),
                "ステータス": task.status,
                "期限": task.due_date or date.today(),
            }
            for task in tasks
        ]

    def _request_rows(self, tasks, label: str):
        names = self._name_map()
        return [
            {
                "区分": label,
                "タイトル": task.title,
                "依頼元": names.get(task.requester_user_id, "-"),
                "担当者": names.get(task.assignee_user_id, "-"),
                "ステータス": task.status,
                "期限": task.due_date,
            }
            for task in tasks
        ]
