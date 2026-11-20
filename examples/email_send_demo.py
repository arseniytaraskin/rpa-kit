import os
from pathlib import Path

from rpa_kit.email_client import SmtpEmailSender
from rpa_kit.exceptions import EmailError


PROJECT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    recipient = os.getenv("EMAIL_TO")

    if not all(
        (
            smtp_host,
            smtp_user,
            smtp_password,
            recipient,
        )
    ):
        print(
            "Задайте переменные SMTP_HOST, SMTP_USER, "
            "SMTP_PASSWORD и EMAIL_TO"
        )
        return 1

    try:
        sender = SmtpEmailSender(
            smtp_host,
            username=smtp_user,
            password=smtp_password,
        )

        message_id = sender.send_html(
            subject="Тестовое письмо rpa-kit",
            sender=smtp_user,
            to=recipient,
            html="<p>Письмо отправлено модулем <b>rpa-kit</b>.</p>",
            text="Письмо отправлено модулем rpa-kit.",
        )

        print(f"Письмо отправлено: {message_id}")
        return 0

    except EmailError as exc:
        print(f"Ошибка: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())