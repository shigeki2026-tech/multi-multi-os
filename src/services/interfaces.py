from abc import ABC, abstractmethod


class CalendarServiceInterface(ABC):
    @abstractmethod
    def get_todays_events(self, user_id: int):
        raise NotImplementedError

    @abstractmethod
    def get_week_events(self, user_id: int):
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> dict:
        raise NotImplementedError


class ReportServiceInterface(ABC):
    @abstractmethod
    def build_preview(self, actor_id: int, payload: dict):
        raise NotImplementedError

    @abstractmethod
    def send_report(self, actor_id: int, payload: dict):
        raise NotImplementedError

    @abstractmethod
    def list_history_for_display(self):
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> dict:
        raise NotImplementedError


class CallDetailServiceInterface(ABC):
    @abstractmethod
    def preview(self):
        raise NotImplementedError


class NotificationServiceInterface(ABC):
    @abstractmethod
    def notify(self, payload: dict):
        raise NotImplementedError
