from sqlalchemy import select

from src.models.entities import Project, Team, User


class MasterRepository:
    def __init__(self, session):
        self.session = session

    def list_users(self):
        return self.session.scalars(select(User).where(User.is_active.is_(True)).order_by(User.user_id)).all()

    def list_teams(self):
        return self.session.scalars(select(Team).order_by(Team.team_id)).all()

    def list_projects(self):
        return self.session.scalars(select(Project).order_by(Project.project_id)).all()

    def get_user(self, user_id: int):
        return self.session.get(User, user_id)
