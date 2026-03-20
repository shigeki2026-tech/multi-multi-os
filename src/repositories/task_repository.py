from datetime import date

from sqlalchemy import and_, select

from src.models.entities import Task, TaskComment


class TaskRepository:
    def __init__(self, session):
        self.session = session

    def list_tasks(self, assignee_user_id=None, include_requests=True, exclude_completed=False, include_archived=False):
        conditions = []
        if include_archived:
            conditions.append(Task.is_active.is_(False))
        else:
            conditions.extend([Task.deleted_at.is_(None), Task.is_active.is_(True)])
        if assignee_user_id:
            conditions.append(Task.assignee_user_id == assignee_user_id)
        if not include_requests:
            conditions.append(Task.task_type != "sv_request")
        if exclude_completed:
            conditions.append(Task.status != "完了")
        stmt = select(Task).where(and_(*conditions)).order_by(Task.due_date.is_(None), Task.due_date, Task.updated_at.desc())
        return self.session.scalars(stmt).all()

    def list_requests(self):
        stmt = select(Task).where(
            Task.task_type == "sv_request",
            Task.deleted_at.is_(None),
            Task.is_active.is_(True),
        ).order_by(Task.created_at.desc())
        return self.session.scalars(stmt).all()

    def list_overdue_tasks(self, assignee_user_id=None):
        conditions = [
            Task.deleted_at.is_(None),
            Task.is_active.is_(True),
            Task.due_date.is_not(None),
            Task.due_date < date.today(),
            Task.status != "完了",
        ]
        if assignee_user_id:
            conditions.append(Task.assignee_user_id == assignee_user_id)
        return self.session.scalars(select(Task).where(and_(*conditions)).order_by(Task.due_date)).all()

    def list_today_due_tasks(self, assignee_user_id=None):
        conditions = [
            Task.deleted_at.is_(None),
            Task.is_active.is_(True),
            Task.due_date == date.today(),
            Task.status != "完了",
        ]
        if assignee_user_id:
            conditions.append(Task.assignee_user_id == assignee_user_id)
        return self.session.scalars(select(Task).where(and_(*conditions)).order_by(Task.updated_at.desc())).all()

    def get_task(self, task_id: int):
        return self.session.get(Task, task_id)

    def create_task(self, task: Task):
        self.session.add(task)
        self.session.flush()
        return task

    def add_comment(self, comment: TaskComment):
        self.session.add(comment)
        self.session.flush()
        return comment

    def list_comments(self, task_id: int):
        stmt = select(TaskComment).where(TaskComment.task_id == task_id).order_by(TaskComment.created_at.desc())
        return self.session.scalars(stmt).all()
