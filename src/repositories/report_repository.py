from sqlalchemy import select

from src.models.entities import ReportJob


class ReportRepository:
    def __init__(self, session):
        self.session = session

    def create_job(self, job: ReportJob):
        self.session.add(job)
        self.session.flush()
        return job

    def list_jobs(self, limit: int = 20):
        stmt = select(ReportJob).order_by(ReportJob.created_at.desc()).limit(limit)
        return self.session.scalars(stmt).all()
