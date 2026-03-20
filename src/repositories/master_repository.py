from sqlalchemy import select

from src.models.entities import Project, Team, User


class MasterRepository:
    def __init__(self, session):
        self.session = session

    def list_users(self, active_only: bool = True):
        stmt = select(User)
        if active_only:
            stmt = stmt.where(User.is_active.is_(True))
        stmt = stmt.order_by(User.user_id)
        return self.session.scalars(stmt).all()

    def list_teams(self, active_only: bool = False):
        stmt = select(Team)
        if active_only:
            stmt = stmt.where(Team.is_active.is_(True))
        stmt = stmt.order_by(Team.display_order, Team.team_id)
        return self.session.scalars(stmt).all()

    def get_team(self, team_id: int | None):
        if team_id is None:
            return None
        return self.session.get(Team, team_id)

    def create_team(self, team: Team):
        self.session.add(team)
        self.session.flush()
        return team

    def update_team(self, team: Team):
        self.session.add(team)
        self.session.flush()
        return team

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

    def update_user(self, user: User):
        self.session.add(user)
        self.session.flush()
        return user

    def update_last_login(self, user: User):
        self.session.add(user)
        self.session.flush()
        return user
