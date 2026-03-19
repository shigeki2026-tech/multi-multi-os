from copy import deepcopy
from datetime import datetime

from src.models.entities import Task, TaskComment
from src.utils.serializers import to_dict


class TaskService:
    def __init__(self, task_repository, master_repository, audit_service):
        self.task_repository = task_repository
        self.master_repository = master_repository
        self.audit_service = audit_service

    def list_tasks_for_display(self, user_id: int, filters: dict):
        assignee_user_id = user_id if filters.get("mine_only") else None
        tasks = self.task_repository.list_tasks(
            assignee_user_id=assignee_user_id,
            include_requests=False,
            exclude_completed=filters.get("exclude_completed", False),
        )
        today = datetime.today().date()
        if filters.get("today_due"):
            tasks = [x for x in tasks if x.due_date and x.due_date == today]
        if filters.get("overdue_only"):
            tasks = [x for x in tasks if x.due_date and x.due_date < today and x.status != "完了"]

        users = {u.user_id: u.display_name for u in self.master_repository.list_users()}
        return [
            {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "title": task.title,
                "requester": users.get(task.requester_user_id, "-"),
                "assignee": users.get(task.assignee_user_id, "-"),
                "priority": task.priority,
                "status": task.status,
                "due_date": task.due_date,
                "needs_confirmation": task.needs_confirmation,
            }
            for task in tasks
        ]

    def create_task(self, actor_id: int, payload: dict):
        task = Task(**payload)
        self.task_repository.create_task(task)
        self.audit_service.log("tasks", task.task_id, "create", actor_id, after=task)
        return task

    def update_task(self, task_id: int, actor_id: int, payload: dict):
        task = self.task_repository.get_task(task_id)
        before = deepcopy(to_dict(task))
        for key, value in payload.items():
            setattr(task, key, value)
        if task.status == "完了" and not task.completed_at:
            task.completed_at = datetime.utcnow()
        self.task_repository.session.flush()
        self.audit_service.log("tasks", task.task_id, "update", actor_id, before=_DictProxy(before), after=task)
        return task

    def change_status(self, task_id: int, status: str, actor_id: int):
        task = self.task_repository.get_task(task_id)
        before = deepcopy(to_dict(task))
        task.status = status
        if status == "完了":
            task.completed_at = datetime.utcnow()
        self.task_repository.session.flush()
        self.audit_service.log("tasks", task.task_id, "status_change", actor_id, before=_DictProxy(before), after=task)
        return task

    def add_comment(self, task_id: int, actor_id: int, comment_text: str):
        comment = TaskComment(task_id=task_id, comment_by=actor_id, comment_text=comment_text)
        self.task_repository.add_comment(comment)
        self.audit_service.log("task_comments", comment.comment_id, "create", actor_id, after=comment)
        return comment

    def get_task_detail(self, task_id: int):
        task = self.task_repository.get_task(task_id)
        users = {u.user_id: u.display_name for u in self.master_repository.list_users()}
        return {
            "task_id": task.task_id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date,
            "related_link": task.related_link,
            "requested_date": task.requested_date,
            "acknowledged_at": task.acknowledged_at,
            "completed_at": task.completed_at,
            "requester_user_id": task.requester_user_id,
            "requester_name": users.get(task.requester_user_id, "-"),
            "assignee_user_id": task.assignee_user_id,
            "assignee_name": users.get(task.assignee_user_id, "-"),
        }

    def task_options(self, include_requests=True):
        tasks = self.task_repository.list_tasks(include_requests=include_requests)
        return [{"value": x.task_id, "label": f"#{x.task_id} {x.title} [{x.status}]"} for x in tasks]

    def get_comments_display(self, task_id: int):
        user_map = {u.user_id: u.display_name for u in self.master_repository.list_users()}
        return [
            {
                "created_at": x.created_at,
                "comment_by": user_map.get(x.comment_by, x.comment_by),
                "comment_text": x.comment_text,
            }
            for x in self.task_repository.list_comments(task_id)
        ]


class _DictProxy:
    def __init__(self, data: dict):
        self.__table__ = type("TableRef", (), {"columns": []})()
        for key, value in data.items():
            self.__table__.columns.append(type("Column", (), {"name": key})())
            setattr(self, key, value)
