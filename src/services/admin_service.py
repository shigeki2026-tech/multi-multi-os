class AdminService:
    def __init__(self, admin_repository):
        self.admin_repository = admin_repository

    def list_apps(self):
        mapping = {
            "tasks": "pages/02_tasks.py",
            "requests": "pages/03_requests.py",
            "leoc": "pages/05_leoc.py",
            "reports": "pages/06_reports.py",
            "call_details": "pages/07_call_details.py",
        }
        return [
            {
                "app_id": x.app_id,
                "app_key": x.app_key,
                "app_name": x.app_name,
                "description": x.description,
                "page": mapping.get(x.app_key, "app.py"),
            }
            for x in self.admin_repository.list_apps()
        ]
