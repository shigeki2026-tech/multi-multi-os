import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    return int(value)


@dataclass(frozen=True)
class AppConfig:
    google_calendar_enabled: bool
    google_calendar_id: str
    google_service_account_file: str
    timezone: str
    gmail_enabled: bool
    gmail_smtp_host: str
    gmail_smtp_port: int
    gmail_from_address: str
    gmail_app_password: str
    report_default_to: str


def get_config() -> AppConfig:
    return AppConfig(
        google_calendar_enabled=_as_bool(os.getenv("GOOGLE_CALENDAR_ENABLED"), default=False),
        google_calendar_id=os.getenv("GOOGLE_CALENDAR_ID", "").strip(),
        google_service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip(),
        timezone=os.getenv("TIMEZONE", "Asia/Tokyo").strip() or "Asia/Tokyo",
        gmail_enabled=_as_bool(os.getenv("GMAIL_ENABLED"), default=False),
        gmail_smtp_host=os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com").strip() or "smtp.gmail.com",
        gmail_smtp_port=_as_int(os.getenv("GMAIL_SMTP_PORT"), 587),
        gmail_from_address=os.getenv("GMAIL_FROM_ADDRESS", "").strip(),
        gmail_app_password=os.getenv("GMAIL_APP_PASSWORD", "").strip(),
        report_default_to=os.getenv("REPORT_DEFAULT_TO", "").strip(),
    )
