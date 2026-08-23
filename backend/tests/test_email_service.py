from email.message import EmailMessage

from app.config import Settings
from app.services.email import EmailSender


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_args: tuple[str, str] | None = None
        self.message: EmailMessage | None = None
        self.__class__.instances.append(self)

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def ehlo(self) -> None:
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.login_args = (username, password)

    def send_message(self, message: EmailMessage) -> None:
        self.message = message


def test_smtp_provider_sends_account_link_with_starttls(monkeypatch) -> None:
    FakeSMTP.instances.clear()
    monkeypatch.setattr("app.services.email.smtplib.SMTP", FakeSMTP)
    settings = Settings(
        email_provider="smtp",
        email_from="Paymentor <ishita.hustlelab@gmail.com>",
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_username="ishita.hustlelab@gmail.com",
        smtp_app_password="abcd efgh ijkl mnop",
    )

    assert settings.email_configured is True
    EmailSender(settings).send_account_link(
        to="owner@example.com",
        name="Owner",
        purpose="verify_email",
        url="https://paymentor.example/verify-email?token=secret",
    )

    smtp = FakeSMTP.instances[0]
    assert (smtp.host, smtp.port, smtp.timeout) == ("smtp.gmail.com", 587, 15)
    assert smtp.started_tls is True
    assert smtp.login_args == ("ishita.hustlelab@gmail.com", "abcdefghijklmnop")
    assert smtp.message is not None
    assert smtp.message["To"] == "owner@example.com"
    assert smtp.message["Subject"] == "Verify your Paymentor email"
    html_part = smtp.message.get_body(preferencelist=("html",))
    assert html_part is not None
    assert "https://paymentor.example/verify-email?token=secret" in html_part.get_content()


def test_incomplete_smtp_configuration_is_not_configured() -> None:
    settings = Settings(email_provider="smtp", smtp_host="smtp.gmail.com")
    assert settings.email_configured is False
