from sqlalchemy import and_, select

from src.models.entities import Task


class RequestRepository:
    def __init__(self, session):
        self.session = session

    def list_received(self, assignee_user_id: int, only_unack=False):
        conditions = [Task.task_type == "sv_request", Task.assignee_user_id == assignee_user_id, Task.deleted_at.is_(None)]
        if only_unack:
            conditions.append(Task.acknowledged_at.is_(None))
        stmt = select(Task).where(and_(*conditions)).order_by(Task.created_at.desc())
        return self.session.scalars(stmt).all()

    def list_sent(self, requester_user_id: int):
        stmt = (
            select(Task)
            .where(Task.task_type == "sv_request", Task.requester_user_id == requester_user_id, Task.deleted_at.is_(None))
            .order_by(Task.created_at.desc())
        )
        return self.session.scalars(stmt).all()
