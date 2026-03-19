class AdminService:
    def __init__(self, admin_repository):
        self.admin_repository = admin_repository

    def list_apps(self):
        mapping = {
            "tasks": "pages/02_タスク.py",
            "requests": "pages/03_SV依頼.py",
            "leoc": "pages/05_応答率速報.py",
            "reports": "pages/06_日報送信.py",
            "call_details": "pages/07_呼詳細作成.py",
        }
        names = {
            "tasks": "タスク",
            "requests": "SV依頼",
            "leoc": "応答率速報",
            "reports": "日報送信",
            "call_details": "呼詳細作成",
        }
        return [
            {
                "app_id": app.app_id,
                "app_key": app.app_key,
                "app_name": names.get(app.app_key, app.app_name),
                "description": app.description,
                "page": mapping.get(app.app_key, "app.py"),
            }
            for app in self.admin_repository.list_apps()
        ]
