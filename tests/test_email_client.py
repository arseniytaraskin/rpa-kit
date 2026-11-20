from email.message import EmailMessage
from unittest.mock import Mock, patch

import pytest

from rpa_kit.email_client import (
    EmailMessageBuilder,
    SmtpEmailSender,
    ImapEmailReader,
    validate_email,
    validate_recipients,
)
from rpa_kit.exceptions import (
    EmailAuthenticationError,
    EmailError,
)


def test_validate_email():
    assert validate_email("user@example.com") == "user@example.com"


@pytest.mark.parametrize(
    "address",
    ["", "user", "user@", "@example.com", "user example.com"],
)
def test_invalid_email(address):
    with pytest.raises(EmailError):
        validate_email(address)


def test_validate_recipients():
    result = validate_recipients(
        ["a@example.com", "b@example.com"]
    )

    assert result == [
        "a@example.com",
        "b@example.com",
    ]


def test_empty_recipients():
    with pytest.raises(EmailError):
        validate_recipients([])


def test_text_message():
    message = EmailMessageBuilder(
        subject="Тест",
        sender="robot@example.com",
        to="user@example.com",
    ).text("Привет").build()

    assert message["Subject"] == "Тест"
    assert message["From"] == "robot@example.com"
    assert message["To"] == "user@example.com"


def test_html_message():
    message = EmailMessageBuilder(
        subject="Тест",
        sender="robot@example.com",
        to="user@example.com",
    ).html(
        "<p>Привет</p>",
        fallback_text="Привет",
    ).build()

    assert message.is_multipart()


def test_attach_missing_file(tmp_path):
    builder = EmailMessageBuilder(
        subject="Тест",
        sender="robot@example.com",
        to="user@example.com",
    )

    with pytest.raises(EmailError):
        builder.attach_file(tmp_path / "missing.txt")


def test_smtp_requires_host():
    with pytest.raises(EmailError):
        SmtpEmailSender("")


def test_smtp_invalid_timeout():
    with pytest.raises(EmailError):
        SmtpEmailSender(
            "smtp.example.com",
            timeout=0,
        )


def test_send_text():
    sender = SmtpEmailSender("smtp.example.com")
    client = Mock()
    client.send_message.return_value = {}

    with patch.object(
        sender,
        "_connection",
    ) as connection:
        connection.return_value.__enter__.return_value = client

        message_id = sender.send_text(
            subject="Тест",
            sender="robot@example.com",
            to="user@example.com",
            body="Привет",
        )

        client.send_message.assert_called_once()

    assert isinstance(message_id, str)


def test_smtp_authentication_error():
    sender = SmtpEmailSender(
        "smtp.example.com",
        username="robot@example.com",
        password="wrong",
    )

    with patch(
        "rpa_kit.email_client.SMTP"
    ) as smtp:
        smtp.return_value.starttls.return_value = None
        smtp.return_value.login.side_effect = Exception(
            "auth"
        )

        with pytest.raises(EmailError):
            sender.send_text(
                subject="Тест",
                sender="robot@example.com",
                to="user@example.com",
                body="Привет",
            )


def test_imap_requires_host():
    with pytest.raises(EmailError):
        ImapEmailReader(
            "",
            username="robot@example.com",
            password="password",
        )


def test_imap_invalid_recipient():
    with pytest.raises(EmailError):
        ImapEmailReader(
            "imap.example.com",
            username="invalid",
            password="password",
        )