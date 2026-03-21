class AdminService:
    def __init__(self, admin_repository):
        self.admin_repository = admin_repository

    def list_apps(self):
        mapping = {
            "tasks": "pages/02_\u30bf\u30b9\u30af.py",
            "requests": "pages/03_SV\u4f9d\u983c.py",
            "leoc": "pages/05_\u5fdc\u7b54\u7387\u901f\u5831.py",
            "reports": "pages/06_\u65e5\u5831\u9001\u4fe1.py",
            "call_details": "pages/07_\u547c\u8a73\u7d30\u4f5c\u6210.py",
            "attendance": "pages/08_\u6253\u523b\u7167\u5408.py",
        }
        names = {
            "tasks": "\u30bf\u30b9\u30af",
            "requests": "SV\u4f9d\u983c",
            "leoc": "\u5fdc\u7b54\u7387\u901f\u5831",
            "reports": "\u65e5\u5831\u9001\u4fe1",
            "call_details": "\u547c\u8a73\u7d30\u4f5c\u6210",
            "attendance": "\u6253\u523b\u7167\u5408",
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
