from src.models.entities import AuditLog
from src.utils.serializers import to_dict


class AuditService:
    def __init__(self, audit_repository):
        self.audit_repository = audit_repository

    def log(self, table_name: str, record_id: str, action_type: str, changed_by: int | None, before=None, after=None):
        log = AuditLog(
            table_name=table_name,
            record_id=str(record_id),
            action_type=action_type,
            changed_by=changed_by,
            before_json=to_dict(before) if before else None,
            after_json=to_dict(after) if after else None,
        )
        self.audit_repository.create(log)

    def list_audit_logs_for_display(self):
        rows = []
        for item in self.audit_repository.list_logs():
            rows.append(
                {
                    "changed_at": item.changed_at,
                    "table_name": item.table_name,
                    "record_id": item.record_id,
                    "action_type": item.action_type,
                    "changed_by": item.changed_by,
                }
            )
        return rows
