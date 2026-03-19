from src.services.interfaces import NotificationServiceInterface


class NotificationService(NotificationServiceInterface):
    def notify(self, payload: dict):
        # TODO: Teams 通知などの外部通知を実装する
        return {"implemented": False, "payload": payload}
