from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.services.interfaces import CalendarServiceInterface
from src.utils.config import get_config


class MockCalendarService(CalendarServiceInterface):
    def __init__(self, message: str | None = None):
        self._status = {
            "source": "mock",
            "configured": False,
            "enabled": False,
            "using_mock": True,
            "error": False,
            "message": message or "Google Calendar API が未設定のため、ダミー予定を表示しています。",
        }

    def get_todays_events(self, user_id: int):
        today = datetime.now().date().isoformat()
        return [
            {"date": today, "time": "09:30", "title": "朝会"},
            {"date": today, "time": "11:00", "title": "案件レビュー"},
            {"date": today, "time": "15:00", "title": "SV引継ぎ"},
        ]

    def get_week_events(self, user_id: int):
        today = datetime.now().date()
        return [
            {"date": (today + timedelta(days=offset)).isoformat(), "time": "10:00", "title": f"ダミー予定 {offset + 1}"}
            for offset in range(5)
        ]

    def get_status(self) -> dict:
        return self._status


class GoogleCalendarService(CalendarServiceInterface):
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(self, calendar_id: str, service_account_file: str, timezone: str):
        self.calendar_id = calendar_id
        self.service_account_file = service_account_file
        self.timezone = timezone
        self._status = {
            "source": "google",
            "configured": True,
            "enabled": True,
            "using_mock": False,
            "error": False,
            "message": "Google Calendar API から予定を取得しています。",
        }

    def get_todays_events(self, user_id: int):
        start, end = self._today_window()
        return self._fetch_events(start, end)

    def get_week_events(self, user_id: int):
        start = self._now()
        end = start + timedelta(days=7)
        return self._fetch_events(start, end)

    def get_status(self) -> dict:
        return self._status

    def _fetch_events(self, time_min: datetime, time_max: datetime):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=self.SCOPES,
            )
            service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
            result = (
                service.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=time_min.isoformat(),
                    timeMax=time_max.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            return [self._normalize_event(item) for item in result.get("items", [])]
        except Exception as exc:
            self._status = {
                "source": "google",
                "configured": True,
                "enabled": True,
                "using_mock": False,
                "error": True,
                "message": f"Google Calendar の取得に失敗しました: {exc}",
            }
            return []

    def _normalize_event(self, item: dict):
        start_data = item.get("start", {})
        start_value = start_data.get("dateTime") or start_data.get("date", "")
        if "T" in start_value:
            start_dt = datetime.fromisoformat(start_value.replace("Z", "+00:00")).astimezone(ZoneInfo(self.timezone))
            return {
                "date": start_dt.date().isoformat(),
                "time": start_dt.strftime("%H:%M"),
                "title": item.get("summary", "(タイトルなし)"),
            }
        return {
            "date": start_value,
            "time": "終日",
            "title": item.get("summary", "(タイトルなし)"),
        }

    def _today_window(self):
        now = self._now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return start, end

    def _now(self):
        return datetime.now(ZoneInfo(self.timezone))


def build_calendar_service() -> CalendarServiceInterface:
    config = get_config()
    if not config.google_calendar_enabled:
        return MockCalendarService("GOOGLE_CALENDAR_ENABLED が false のため、ダミー予定を表示しています。")
    if not config.google_calendar_id or not config.google_service_account_file:
        return MockCalendarService("Google Calendar の設定が不足しているため、ダミー予定を表示しています。")
    return GoogleCalendarService(
        calendar_id=config.google_calendar_id,
        service_account_file=config.google_service_account_file,
        timezone=config.timezone,
    )
