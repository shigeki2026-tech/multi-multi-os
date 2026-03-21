from contextlib import contextmanager

from src.repositories.admin_repository import AdminRepository
from src.repositories.attendance_repository import AttendanceRepository
from src.repositories.audit_repository import AuditRepository
from src.repositories.db import get_session
from src.repositories.leoc_repository import LeocRepository
from src.repositories.master_repository import MasterRepository
from src.repositories.report_repository import ReportRepository
from src.repositories.request_repository import RequestRepository
from src.repositories.task_repository import TaskRepository
from src.services.admin_service import AdminService
from src.services.attendance_service import AttendanceService
from src.services.audit_service import AuditService
from src.services.calendar_service import build_calendar_service
from src.services.call_detail_service import CallDetailService
from src.services.dashboard_service import DashboardService
from src.services.gmail_service import GmailService
from src.services.leoc_service import LeocService
from src.services.master_service import MasterService
from src.services.notification_service import NotificationService
from src.services.report_service import ReportService
from src.services.request_service import RequestService
from src.services.task_service import TaskService
from src.utils.config import get_config


class ServiceContainer:
    def __init__(self, session):
        self.session = session
        self.config = get_config()

        self.master_repository = MasterRepository(session)
        self.task_repository = TaskRepository(session)
        self.request_repository = RequestRepository(session)
        self.report_repository = ReportRepository(session)
        self.leoc_repository = LeocRepository(session)
        self.audit_repository = AuditRepository(session)
        self.admin_repository = AdminRepository(session)
        self.attendance_repository = AttendanceRepository(session)

        self.audit_service = AuditService(self.audit_repository)
        self.master_service = MasterService(self.master_repository, self.audit_service)
        self.task_service = TaskService(self.task_repository, self.master_repository, self.audit_service)
        self.request_service = RequestService(self.task_service, self.request_repository, self.master_repository)
        self.calendar_service = build_calendar_service()
        self.leoc_service = LeocService(self.leoc_repository, self.audit_service)
        self.gmail_service = GmailService(self.config)
        self.report_service = ReportService(
            self.report_repository,
            self.audit_service,
            self.master_repository,
            self.gmail_service,
            self.config,
        )
        self.call_detail_service = CallDetailService()
        self.notification_service = NotificationService()
        self.dashboard_service = DashboardService(
            self.task_repository,
            self.request_repository,
            self.calendar_service,
            self.leoc_service,
            self.master_repository,
        )
        self.admin_service = AdminService(self.admin_repository)
        self.attendance_service = AttendanceService(self.attendance_repository, self.audit_service)


@contextmanager
def service_scope():
    with get_session() as session:
        yield ServiceContainer(session)
