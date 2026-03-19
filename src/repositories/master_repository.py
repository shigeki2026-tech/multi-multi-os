from sqlalchemy import select

from src.models.entities import Project, Team, User


class MasterRepository:
    def __init__(self, session):
        self.session = session

    def list_users(self):
        return self.session.scalars(select(User).where(User.is_active.is_(True)).order_by(User.user_id)).all()

    def list_teams(self):
        return self.session.scalars(select(Team).order_by(Team.team_id)).all()

    def list_projects(self, active_only: bool = False):
        stmt = select(Project)
        if active_only:
            stmt = stmt.where(Project.is_active.is_(True))
        stmt = stmt.order_by(Project.display_order, Project.project_id)
        return self.session.scalars(stmt).all()

    def get_project(self, project_id: int):
        return self.session.get(Project, project_id)

    def create_project(self, project: Project):
        self.session.add(project)
        self.session.flush()
        return project

    def get_user(self, user_id: int):
        return self.session.get(User, user_id)
