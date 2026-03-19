import smtplib
from email.message import EmailMessage


class GmailService:
    def __init__(self, config):
        self.config = config

    def get_status(self) -> dict:
        configured = all(
            [
                self.config.gmail_enabled,
                self.config.gmail_from_address,
                self.config.gmail_app_password,
            ]
        )
        return {
            "enabled": self.config.gmail_enabled,
            "configured": configured,
            "message": "Gmail SMTP 送信が利用可能です。"
            if configured
            else "Gmail SMTP の設定が未完了です。プレビューと履歴保存のみ利用できます。",
        }

    def send_email(self, to_addresses: list[str], subject: str, body: str):
        if not self.get_status()["configured"]:
            raise ValueError("Gmail SMTP の設定が不足しています。")
        if not to_addresses:
            raise ValueError("送信先が設定されていません。")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.config.gmail_from_address
        message["To"] = ", ".join(to_addresses)
        message.set_content(body)

        try:
            with smtplib.SMTP(self.config.gmail_smtp_host, self.config.gmail_smtp_port, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(self.config.gmail_from_address, self.config.gmail_app_password)
                smtp.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            raise RuntimeError(f"Gmail 認証に失敗しました: {exc}") from exc
        except smtplib.SMTPConnectError as exc:
            raise RuntimeError(f"SMTP 接続に失敗しました: {exc}") from exc
        except (smtplib.SMTPException, OSError) as exc:
            raise RuntimeError(f"メール送信に失敗しました: {exc}") from exc
