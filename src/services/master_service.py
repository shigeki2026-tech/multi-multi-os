from copy import deepcopy

import streamlit as st

from src.models.entities import Project, Team, User
from src.utils.serializers import to_dict


# ---------------------------------------------------------------------------
# モジュールレベルのキャッシュ関数
# @st.cache_data はハッシュ可能な引数が必要なため、
# インスタンスメソッドではなく db_url: str をキーにする独立関数として定義する
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def _cached_user_options(db_url: str) -> list:
    from src.repositories.db import get_session
    from src.repositories.master_repository import MasterRepository
    with get_session() as session:
        repo = MasterRepository(session)
        teams = {team.team_id: team.team_name for team in repo.list_teams()}
        return [
            {
                "value": user.user_id,
                "label": f"{user.display_name} / {user.role} / {teams.get(user.team_id, 'チーム未設定')}",
            }
            for user in repo.list_users(active_only=True)
        ]


@st.cache_data(ttl=300)
def _cached_team_options(db_url: str) -> list:
    from src.repositories.db import get_session
    from src.repositories.master_repository import MasterRepository
    with get_session() as session:
        repo = MasterRepository(session)
        return [
            {"value": team.team_id, "label": team.team_name}
            for team in repo.list_teams(active_only=True)
        ]


@st.cache_data(ttl=300)
def _cached_project_options(db_url: str) -> list:
    from src.repositories.db import get_session
    from src.repositories.master_repository import MasterRepository
    with get_session() as session:
        repo = MasterRepository(session)
        return [
            {"value": project.project_id, "label": project.project_name, "color": project.color}
            for project in repo.list_projects(active_only=True)
        ]


# ---------------------------------------------------------------------------
# MasterService
# ---------------------------------------------------------------------------

class MasterService:
    def __init__(self, master_repository, audit_service=None):
        self.master_repository = master_repository
        self.audit_service = audit_service

    def user_options(self):
        from src.repositories.db import DATABASE_URL
        return _cached_user_options(DATABASE_URL)

    def list_users_for_admin(self):
        teams = {team.team_id: team.team_name for team in self.master_repository.list_teams()}
        return [
            {
                "user_id": user.user_id,
                "display_name": user.display_name,
                "google_email": user.google_email or "-",
                "role": user.role,
                "team_id": user.team_id,
                "team_name": teams.get(user.team_id, "チーム未設定"),
                "is_active": user.is_active,
                "last_login_at": user.last_login_at,
            }
            for user in self.master_repository.list_users(active_only=False)
        ]

    def update_user(self, user_id: int, actor_id: int, payload: dict):
        user = self.master_repository.get_user(user_id)
        before = deepcopy(to_dict(user))
        for key, value in payload.items():
            setattr(user, key, value)
        self.master_repository.update_user(user)
        if self.audit_service:
            self.audit_service.log("users", user.user_id, "update", actor_id, before=_DictProxy(before), after=user)
        return user

    def create_user(self, actor_id: int, payload: dict):
        existing = self.master_repository.get_user_by_google_email(payload["google_email"])
        if existing:
            raise ValueError("同じ Googleメール のユーザーが既に存在します。")
        user = User(
            google_email=payload["google_email"],
            email=payload["google_email"],
            display_name=payload["display_name"],
            role=payload["role"],
            team_id=payload["team_id"],
            is_active=payload["is_active"],
        )
        self.master_repository.create_user(user)
        if self.audit_service:
            self.audit_service.log("users", user.user_id, "create", actor_id, after=user)
        return user

    def team_options(self):
        from src.repositories.db import DATABASE_URL
        return _cached_team_options(DATABASE_URL)

    def list_teams_for_admin(self):
        return [
            {
                "team_id": team.team_id,
                "team_name": team.team_name,
                "display_order": team.display_order,
                "is_active": team.is_active,
                "description": team.description or "",
            }
            for team in self.master_repository.list_teams(active_only=False)
        ]

    def create_team(self, actor_id: int, payload: dict):
        team = Team(**payload)
        self.master_repository.create_team(team)
        if self.audit_service:
            self.audit_service.log("teams", team.team_id, "create", actor_id, after=team)
        return team

    def update_team(self, team_id: int, actor_id: int, payload: dict):
        team = self.master_repository.get_team(team_id)
        before = deepcopy(to_dict(team))
        for key, value in payload.items():
            setattr(team, key, value)
        self.master_repository.update_team(team)
        if self.audit_service:
            self.audit_service.log("teams", team.team_id, "update", actor_id, before=_DictProxy(before), after=team)
        return team

    def project_options(self):
        from src.repositories.db import DATABASE_URL
        return _cached_project_options(DATABASE_URL)

    def list_projects_for_admin(self):
        teams = {team.team_id: team.team_name for team in self.master_repository.list_teams()}
        return [
            {
                "project_id": project.project_id,
                "project_name": project.project_name,
                "team_name": teams.get(project.team_id, "-"),
                "team_id": project.team_id,
                "color": project.color,
                "display_order": project.display_order,
                "is_active": project.is_active,
            }
            for project in self.master_repository.list_projects(active_only=False)
        ]

    def create_project(self, actor_id: int, payload: dict):
        project = Project(**payload)
        self.master_repository.create_project(project)
        if self.audit_service:
            self.audit_service.log("projects", project.project_id, "create", actor_id, after=project)
        return project

    def update_project(self, project_id: int, actor_id: int, payload: dict):
        project = self.master_repository.get_project(project_id)
        before = deepcopy(to_dict(project))
        for key, value in payload.items():
            setattr(project, key, value)
        self.master_repository.session.flush()
        if self.audit_service:
            self.audit_service.log("projects", project.project_id, "update", actor_id, before=_DictProxy(before), after=project)
        return project

    def list_users(self):
        return self.master_repository.list_users(active_only=False)

    def get_user(self, user_id: int):
        return self.master_repository.get_user(user_id)


class _DictProxy:
    def __init__(self, data: dict):
        self.__table__ = type("TableRef", (), {"columns": []})()
        for key, value in data.items():
            self.__table__.columns.append(type("Column", (), {"name": key})())
            setattr(self, key, value)
