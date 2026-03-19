from copy import deepcopy
from datetime import datetime

from src.utils.serializers import to_dict


class RequestService:
    def __init__(self, task_service, request_repository, master_repository):
        self.task_service = task_service
        self.request_repository = request_repository
        self.master_repository = master_repository

    def create_request(self, actor_id: int, payload: dict):
        payload["task_type"] = "sv_request"
        return self.task_service.create_task(actor_id, payload)

    def list_received_for_display(self, user_id: int, only_unack: bool):
        return [self._to_row(x) for x in self.request_repository.list_received(user_id, only_unack)]

    def list_sent_for_display(self, user_id: int):
        return [self._to_row(x) for x in self.request_repository.list_sent(user_id)]

    def request_options(self):
        return [
            {"value": x.task_id, "label": f"#{x.task_id} {x.title} [{x.status}]"}
            for x in self.task_service.task_repository.list_requests()
        ]

    def get_request_detail(self, task_id: int):
        detail = self.task_service.get_task_detail(task_id)
        return {
            "依頼ID": detail["task_id"],
            "title": detail["title"],
            "description": detail["description"],
            "依頼元": detail["requester_name"],
            "担当者": detail["assignee_name"],
            "status": detail["status"],
            "priority": detail["priority"],
            "due_date": detail["due_date"],
            "requested_date": detail["requested_date"],
            "acknowledged_at": detail["acknowledged_at"],
            "completed_at": detail["completed_at"],
            "related_link": detail["related_link"],
        }

    def acknowledge_request(self, task_id: int, actor_id: int):
        task = self.task_service.task_repository.get_task(task_id)
        before = deepcopy(to_dict(task))
        task.acknowledged_at = datetime.utcnow()
        task.status = "進行中"
        self.task_service.task_repository.session.flush()
        self.task_service.audit_service.log("tasks", task.task_id, "acknowledge", actor_id, before=_DictProxy(before), after=task)
        return task

    def change_status(self, task_id: int, status: str, actor_id: int):
        return self.task_service.change_status(task_id, status, actor_id)

    def add_comment(self, task_id: int, actor_id: int, comment_text: str):
        return self.task_service.add_comment(task_id, actor_id, comment_text)

    def get_comments_display(self, task_id: int):
        return self.task_service.get_comments_display(task_id)

    def _to_row(self, task):
        users = {user.user_id: user.display_name for user in self.master_repository.list_users()}
        return {
            "task_id": task.task_id,
            "title": task.title,
            "requester": users.get(task.requester_user_id, "-"),
            "assignee": users.get(task.assignee_user_id, "-"),
            "priority": task.priority,
            "status": task.status,
            "requested_date": task.requested_date,
            "due_date": task.due_date,
            "acknowledged_at": task.acknowledged_at,
            "completed_at": task.completed_at,
        }


class _DictProxy:
    def __init__(self, data: dict):
        self.__table__ = type("TableRef", (), {"columns": []})()
        for key, value in data.items():
            self.__table__.columns.append(type("Column", (), {"name": key})())
            setattr(self, key, value)
