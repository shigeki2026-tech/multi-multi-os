from sqlalchemy import select

from src.models.entities import AuditLog


class AuditRepository:
    def __init__(self, session):
        self.session = session

    def create(self, audit_log: AuditLog):
        self.session.add(audit_log)
        self.session.flush()
        return audit_log

    def list_logs(self):
        stmt = select(AuditLog).order_by(AuditLog.changed_at.desc())
        return self.session.scalars(stmt).all()
