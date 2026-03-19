from copy import deepcopy

from src.models.entities import Project
from src.utils.serializers import to_dict


class MasterService:
    def __init__(self, master_repository, audit_service=None):
        self.master_repository = master_repository
        self.audit_service = audit_service

    def user_options(self):
        return [{"value": x.user_id, "label": f"{x.display_name} ({x.role})"} for x in self.master_repository.list_users()]

    def team_options(self):
        return [{"value": x.team_id, "label": x.team_name} for x in self.master_repository.list_teams()]

    def project_options(self):
        return [
            {"value": x.project_id, "label": x.project_name, "color": x.color}
            for x in self.master_repository.list_projects(active_only=True)
        ]

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
        return self.master_repository.list_users()

    def get_user(self, user_id: int):
        return self.master_repository.get_user(user_id)


class _DictProxy:
    def __init__(self, data: dict):
        self.__table__ = type("TableRef", (), {"columns": []})()
        for key, value in data.items():
            self.__table__.columns.append(type("Column", (), {"name": key})())
            setattr(self, key, value)
