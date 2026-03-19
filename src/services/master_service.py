class MasterService:
    def __init__(self, master_repository):
        self.master_repository = master_repository

    def user_options(self):
        return [{"value": x.user_id, "label": f"{x.display_name} ({x.role})"} for x in self.master_repository.list_users()]

    def team_options(self):
        return [{"value": x.team_id, "label": x.team_name} for x in self.master_repository.list_teams()]

    def project_options(self):
        return [{"value": x.project_id, "label": x.project_name} for x in self.master_repository.list_projects()]

    def list_users(self):
        return self.master_repository.list_users()

    def get_user(self, user_id: int):
        return self.master_repository.get_user(user_id)
