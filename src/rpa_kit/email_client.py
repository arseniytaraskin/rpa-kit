import re
import ssl
from contextlib import contextmanager
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default
from email.utils import parseaddr
from imaplib import IMAP4_SSL
from pathlib import Path
from smtplib import (
    SMTP,
    SMTPAuthenticationError,
    SMTPException,
    SMTP_SSL,
)
from typing import Any, Iterator
from urllib.parse import quote

from rpa_kit.exceptions import (
    EmailAuthenticationError,
    EmailError,
    EmailTimeoutError,
)


EMAIL_ADDRESS_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)


def validate_email(address: str) -> str:
    if not isinstance(address, str):
        raise EmailError("Адрес должен быть строкой")

    address = address.strip()

    if not EMAIL_ADDRESS_PATTERN.fullmatch(address):
        raise EmailError(f"Некорректный email: {address}")

    return address


def validate_recipients(
    recipients: str | list[str] | tuple[str, ...],
) -> list[str]:
    if isinstance(recipients, str):
        recipients = [recipients]

    if not isinstance(recipients, (list, tuple)):
        raise EmailError(
            "Получатели должны быть строкой или списком строк"
        )

    if not recipients:
        raise EmailError("Укажите хотя бы одного получателя")

    return [
        validate_email(recipient)
        for recipient in recipients
    ]


class EmailMessageBuilder:
    def __init__(
        self,
        *,
        subject: str,
        sender: str,
        to: str | list[str],
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        reply_to: str | None = None,
    ):
        self.message = EmailMessage()
        self.message["Subject"] = subject
        self.message["From"] = validate_email(sender)
        self.message["To"] = ", ".join(
            validate_recipients(to)
        )

        if cc:
            self.message["Cc"] = ", ".join(
                validate_recipients(cc)
            )

        if bcc:
            self.message["Bcc"] = ", ".join(
                validate_recipients(bcc)
            )

        if reply_to:
            self.message["Reply-To"] = validate_email(
                reply_to
            )

    def text(self, content: str) -> "EmailMessageBuilder":
        if not isinstance(content, str):
            raise EmailError("Текст письма должен быть строкой")

        self.message.set_content(content)
        return self

    def html(
        self,
        content: str,
        *,
        fallback_text: str | None = None,
    ) -> "EmailMessageBuilder":
        if not isinstance(content, str):
            raise EmailError("HTML должен быть строкой")

        if fallback_text is not None:
            self.message.set_content(fallback_text)

        self.message.add_alternative(
            content,
            subtype="html",
        )

        return self

    def attach_file(
        self,
        path: str | Path,
        *,
        filename: str | None = None,
    ) -> "EmailMessageBuilder":
        source = Path(path)

        if not source.is_file():
            raise EmailError(
                f"Файл вложения не найден: {source}"
            )

        attachment_name = filename or source.name

        try:
            content = source.read_bytes()
        except OSError as exc:
            raise EmailError(
                f"Не удалось прочитать вложение: {source}"
            ) from exc

        maintype, _, subtype = (
            source.suffix.lower().lstrip(".").partition("/")
        )

        if not maintype:
            maintype = "application"
            subtype = "octet-stream"

        self.message.add_attachment(
            content,
            maintype=maintype,
            subtype=subtype,
            filename=attachment_name,
        )

        return self

    def build(self) -> EmailMessage:
        return self.message


class SmtpEmailSender:
    def __init__(
        self,
        host: str,
        *,
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        use_ssl: bool = False,
        timeout: float = 30,
    ):
        if not host.strip():
            raise EmailError("Укажите SMTP-сервер")

        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or timeout <= 0
        ):
            raise EmailError("timeout должен быть положительным числом")

        self.host = host.strip()
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.timeout = timeout
        self._client = None

    @contextmanager
    def _connection(self) -> Iterator[SMTP]:
        try:
            if self.use_ssl:
                client = SMTP_SSL(
                    self.host,
                    self.port,
                    timeout=self.timeout,
                    context=ssl.create_default_context(),
                )
            else:
                client = SMTP(
                    self.host,
                    self.port,
                    timeout=self.timeout,
                )

            try:
                if not self.use_ssl:
                    client.starttls(
                        context=ssl.create_default_context()
                    )

                if self.username and self.password:
                    client.login(
                        self.username,
                        self.password,
                    )

                yield client

            finally:
                try:
                    client.quit()
                except SMTPException:
                    pass

        except SMTPAuthenticationError as exc:
            raise EmailAuthenticationError(
                "Не удалось авторизоваться на SMTP-сервере"
            ) from exc

        except (TimeoutError, OSError) as exc:
            raise EmailTimeoutError(
                "Не удалось подключиться к SMTP-серверу"
            ) from exc

        except SMTPException as exc:
            raise EmailError(
                "SMTP-сервер отклонил операцию"
            ) from exc

    def send(
        self,
        message: EmailMessage,
        *,
        bcc: str | list[str] | None = None,
    ) -> str:
        sender = message["From"]
        recipients = message.get("To", "").split(", ")
        recipients += message.get("Cc", "").split(", ")

        if bcc:
            recipients += validate_recipients(bcc)

        recipients = [
            recipient
            for recipient in recipients
            if recipient
        ]

        if not recipients:
            raise EmailError("Не указаны получатели")

        with self._connection() as client:
            client.send_message(
                message,
                from_addr=sender,
                to_addrs=recipients,
            )

        return message["Message-ID"] or ""

    def send_text(
        self,
        *,
        subject: str,
        sender: str,
        to: str | list[str],
        body: str,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
    ) -> str:
        message = EmailMessageBuilder(
            subject=subject,
            sender=sender,
            to=to,
            cc=cc,
            bcc=bcc,
        ).text(body).build()

        return self.send(message)

    def send_html(
        self,
        *,
        subject: str,
        sender: str,
        to: str | list[str],
        html: str,
        text: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
    ) -> str:
        message = EmailMessageBuilder(
            subject=subject,
            sender=sender,
            to=to,
            cc=cc,
            bcc=bcc,
        ).html(
            html,
            fallback_text=text,
        ).build()

        return self.send(message)


class ImapEmailReader:
    def __init__(
        self,
        host: str,
        *,
        username: str,
        password: str,
        port: int = 993,
        timeout: float = 30,
    ):
        if not host.strip():
            raise EmailError("Укажите IMAP-сервер")

        validate_email(username)

        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or timeout <= 0
        ):
            raise EmailError("timeout должен быть положительным числом")

        self.host = host.strip()
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self._client = None
        self._mailbox = None

    @contextmanager
    def _connection(self) -> Iterator[IMAP4_SSL]:
        try:
            client = IMAP4_SSL(
                self.host,
                self.port,
                timeout=self.timeout,
            )

            try:
                client.login(
                    self.username,
                    self.password,
                )
                yield client
            finally:
                try:
                    client.logout()
                except Exception:
                    pass

        except Exception as exc:
            if isinstance(exc, EmailError):
                raise

            raise EmailError(
                "Не удалось подключиться к IMAP-серверу"
            ) from exc

    def _require_mailbox(self):
        if self._client is None or self._mailbox is None:
            raise EmailError("Почтовый ящик не выбран")

        return self._client

    def select_mailbox(
        self,
        mailbox: str = "INBOX",
        *,
        readonly: bool = True,
    ) -> int:
        with self._connection() as client:
            status, data = client.select(
                quote(mailbox),
                readonly=readonly,
            )

            if status != "OK":
                raise EmailError(
                    f"Не удалось открыть папку: {mailbox}"
                )

            return int(data[0])

    def search(
        self,
        *,
        mailbox: str = "INBOX",
        unread_only: bool = False,
        since: str | None = None,
        subject: str | None = None,
        sender: str | None = None,
    ) -> list[str]:
        criteria = []

        if unread_only:
            criteria.append("UNSEEN")

        if since:
            criteria.append(f'SINCE "{since}"')

        if subject:
            criteria.append(f'SUBJECT "{subject}"')

        if sender:
            criteria.append(f'FROM "{sender}"')

        if not criteria:
            criteria.append("ALL")

        with self._connection() as client:
            client.select(quote(mailbox), readonly=True)

            status, data = client.search(
                None,
                *criteria,
            )

            if status != "OK":
                raise EmailError(
                    "Не удалось выполнить поиск писем"
                )

            return data[0].split()

    def get_message(
        self,
        message_id: str,
        *,
        mailbox: str = "INBOX",
    ) -> EmailMessage:
        if not message_id:
            raise EmailError("Укажите идентификатор письма")

        with self._connection() as client:
            client.select(quote(mailbox), readonly=True)

            status, data = client.fetch(
                message_id,
                "(RFC822)",
            )

            if status != "OK" or not data or data[0] is None:
                raise EmailError(
                    f"Не удалось получить письмо: {message_id}"
                )

            raw_message = data[0][1]

        return BytesParser(
            policy=default
        ).parsebytes(raw_message)

    def get_text(self, message: EmailMessage) -> str:
        if not message.is_multipart():
            return message.get_content()

        for part in message.walk():
            if (
                part.get_content_type() == "text/plain"
                and not part.get_filename()
            ):
                return part.get_content()

        return ""

    def get_html(self, message: EmailMessage) -> str:
        if not message.is_multipart():
            if message.get_content_type() == "text/html":
                return message.get_content()

            return ""

        for part in message.walk():
            if (
                part.get_content_type() == "text/html"
                and not part.get_filename()
            ):
                return part.get_content()

        return ""

    def save_attachments(
        self,
        message: EmailMessage,
        directory: str | Path,
        *,
        overwrite: bool = False,
    ) -> list[Path]:
        destination = Path(directory)
        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        saved = []

        for part in message.walk():
            filename = part.get_filename()

            if not filename:
                continue

            target = destination / filename

            if target.exists() and not overwrite:
                raise EmailError(
                    f"Файл уже существует: {target}"
                )

            target.write_bytes(part.get_payload(decode=True))
            saved.append(target)

        return saved

    def mark_as_read(
        self,
        message_id: str,
        *,
        mailbox: str = "INBOX",
    ) -> None:
        with self._connection() as client:
            client.select(quote(mailbox), readonly=False)

            status, _ = client.store(
                message_id,
                "+FLAGS",
                "\\Seen",
            )

            if status != "OK":
                raise EmailError(
                    "Не удалось отметить письмо прочитанным"
                )

    def move_message(
        self,
        message_id: str,
        *,
        source_mailbox: str = "INBOX",
        target_mailbox: str = "Archive",
    ) -> None:
        with self._connection() as client:
            client.select(
                quote(source_mailbox),
                readonly=False,
            )

            status, data = client.copy(
                message_id,
                quote(target_mailbox),
            )

            if status != "OK":
                raise EmailError(
                    f"Не удалось скопировать письмо в {target_mailbox}"
                )

            client.store(
                message_id,
                "+FLAGS",
                "\\Deleted",
            )
            client.expunge()