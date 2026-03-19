import re
from datetime import datetime

from src.models.entities import ReportJob
from src.services.interfaces import ReportServiceInterface


class ReportService(ReportServiceInterface):
    EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

    def __init__(self, report_repository, audit_service, master_repository, gmail_service, config):
        self.report_repository = report_repository
        self.audit_service = audit_service
        self.master_repository = master_repository
        self.gmail_service = gmail_service
        self.config = config

    def build_preview(self, actor_id: int, payload: dict):
        user = self.master_repository.get_user(actor_id)
        target_date = payload["target_date"]
        subject = payload.get("subject") or f"{target_date} 日報"
        body = self._build_body(
            display_name=user.display_name if user else "不明",
            target_date=str(target_date),
            summary=payload.get("summary", ""),
            highlights=payload.get("highlights", ""),
            issues=payload.get("issues", ""),
            next_actions=payload.get("next_actions", ""),
        )
        recipients = self._parse_recipients(payload.get("to_addresses", self.config.report_default_to))
        invalid_recipients = [address for address in recipients if not self.EMAIL_PATTERN.match(address)]
        return {
            "subject": subject,
            "body": body,
            "to_addresses": recipients,
            "invalid_to_addresses": invalid_recipients,
        }

    def send_report(self, actor_id: int, payload: dict):
        preview = self.build_preview(actor_id, payload)
        send_status = "draft"
        sent_at = None
        message = "Gmail 設定が未完了のため、送信せず履歴のみ保存しました。"
        error_message = None

        gmail_status = self.gmail_service.get_status()
        if not preview["to_addresses"]:
            send_status = "failed"
            error_message = "送信先が未設定です。"
            message = "送信先が未設定のため送信できません。"
        elif preview["invalid_to_addresses"]:
            send_status = "failed"
            error_message = f"不正なメールアドレスがあります: {', '.join(preview['invalid_to_addresses'])}"
            message = "送信先に不正なメールアドレスがあるため送信できません。"
        elif gmail_status["configured"]:
            try:
                self.gmail_service.send_email(preview["to_addresses"], preview["subject"], preview["body"])
                send_status = "sent"
                sent_at = datetime.utcnow()
                message = "Gmail で送信しました。"
            except Exception as exc:
                send_status = "failed"
                error_message = str(exc)
                message = "Gmail 送信に失敗しました。"

        job = ReportJob(
            report_type=payload.get("report_type", "daily_report"),
            target_date=payload["target_date"],
            payload_json={
                "to_addresses": preview["to_addresses"],
                "invalid_to_addresses": preview["invalid_to_addresses"],
                "summary": payload.get("summary", ""),
                "highlights": payload.get("highlights", ""),
                "issues": payload.get("issues", ""),
                "next_actions": payload.get("next_actions", ""),
                "subject": preview["subject"],
                "error_message": error_message,
            },
            preview_text=preview["body"],
            sent_at=sent_at,
            sent_by=actor_id,
            send_status=send_status,
        )
        self.report_repository.create_job(job)
        self.audit_service.log("report_jobs", job.job_id, "create", actor_id, after=job)
        return {
            "job_id": job.job_id,
            "send_status": send_status,
            "message": message,
            "error_message": error_message,
            "preview": preview,
        }

    def list_history_for_display(self):
        user_map = {user.user_id: user.display_name for user in self.master_repository.list_users()}
        rows = []
        for job in self.report_repository.list_jobs():
            payload = job.payload_json or {}
            rows.append(
                {
                    "job_id": job.job_id,
                    "report_type": job.report_type,
                    "target_date": job.target_date,
                    "to_addresses": ", ".join(payload.get("to_addresses", [])),
                    "subject": payload.get("subject", ""),
                    "send_status": job.send_status,
                    "error_message": payload.get("error_message", ""),
                    "sent_at": job.sent_at,
                    "sent_by": user_map.get(job.sent_by, "-"),
                }
            )
        return rows

    def get_status(self) -> dict:
        return self.gmail_service.get_status()

    def _parse_recipients(self, raw_value: str):
        return [item.strip() for item in str(raw_value).replace("\n", ",").split(",") if item.strip()]

    def _build_body(self, display_name: str, target_date: str, summary: str, highlights: str, issues: str, next_actions: str):
        return "\n".join(
            [
                f"{target_date} 日報",
                f"担当: {display_name}",
                "",
                "【本日の概要】",
                summary or "記載なし",
                "",
                "【実施内容】",
                highlights or "記載なし",
                "",
                "【課題・懸念点】",
                issues or "記載なし",
                "",
                "【明日の対応】",
                next_actions or "記載なし",
            ]
        )
