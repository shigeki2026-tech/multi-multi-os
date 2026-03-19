from sqlalchemy import select

from src.models.entities import LeocSnapshot


class LeocRepository:
    def __init__(self, session):
        self.session = session

    def create_snapshot(self, snapshot: LeocSnapshot):
        self.session.add(snapshot)
        self.session.flush()
        return snapshot

    def list_history(self):
        stmt = select(LeocSnapshot).order_by(LeocSnapshot.created_at.desc())
        return self.session.scalars(stmt).all()

    def latest(self):
        stmt = select(LeocSnapshot).order_by(LeocSnapshot.created_at.desc()).limit(1)
        return self.session.scalars(stmt).first()
