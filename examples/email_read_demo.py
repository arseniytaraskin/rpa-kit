import os
from pathlib import Path

from rpa_kit.email_client import ImapEmailReader
from rpa_kit.exceptions import EmailError


PROJECT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    imap_host = os.getenv("IMAP_HOST")
    imap_user = os.getenv("IMAP_USER")
    imap_password = os.getenv("IMAP_PASSWORD")

    if not all(
        (
            imap_host,
            imap_user,
            imap_password,
        )
    ):
        print(
            "Задайте переменные IMAP_HOST, IMAP_USER и IMAP_PASSWORD"
        )
        return 1

    try:
        reader = ImapEmailReader(
            imap_host,
            username=imap_user,
            password=imap_password,
        )

        message_ids = reader.search(
            unread_only=True,
            limit=5,
        )

        print(f"Найдено писем: {len(message_ids)}")

        for message_id in message_ids:
            message = reader.get_message(message_id)

            print(
                f"{message_id}: {message['Subject']}"
            )

        return 0

    except EmailError as exc:
        print(f"Ошибка: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())