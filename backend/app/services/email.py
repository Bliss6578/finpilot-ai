from __future__ import annotations

from html import escape
from email.message import EmailMessage
import smtplib

import httpx
from fastapi import Depends

from app.config import Settings, get_settings


class EmailSender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send_account_link(self, *, to: str, name: str, purpose: str, url: str) -> None:
        if not self.settings.email_configured:
            raise RuntimeError("Email delivery is not configured")
        if purpose == "verify_email":
            subject = "Verify your Paymentor email"
            heading = "Verify your email"
            message = "Confirm this address to secure your Paymentor workspace."
            action = "Verify email"
        else:
            subject = "Reset your Paymentor password"
            heading = "Reset your password"
            message = "Use this secure, single-use link to choose a new password."
            action = "Reset password"
        safe_name = escape(name)
        safe_url = escape(url, quote=True)
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;padding:32px;color:#241f1b">
          <p style="font-size:13px;letter-spacing:2px;color:#897a6d">PAYMENTOR SECURITY</p>
          <h1 style="font-size:30px">{heading}</h1>
          <p>Hi {safe_name},</p><p>{message}</p>
          <p style="margin:28px 0"><a href="{safe_url}" style="background:#594b40;color:#fff;padding:14px 20px;border-radius:10px;text-decoration:none">{action}</a></p>
          <p style="font-size:12px;color:#776d65">If you did not request this, you can safely ignore this email. Never share this link.</p>
        </div>
        """
        provider = self.settings.email_provider.strip().lower()
        if provider == "smtp":
            self._send_smtp(to=to, subject=subject, html=html)
            return
        if provider == "resend":
            self._send_resend(to=to, subject=subject, html=html)
            return
        raise RuntimeError(f"Unsupported email provider: {provider or 'empty'}")

    def _send_resend(self, *, to: str, subject: str, html: str) -> None:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {self.settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": self.settings.email_from,
                "to": [to],
                "subject": subject,
                "html": html,
            },
            timeout=15,
        )
        response.raise_for_status()

    def _send_smtp(self, *, to: str, subject: str, html: str) -> None:
        message = EmailMessage()
        message["From"] = self.settings.email_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content("Open this email in an HTML-capable client to use the secure Paymentor link.")
        message.add_alternative(html, subtype="html")

        password = self.settings.smtp_app_password.replace(" ", "")
        with smtplib.SMTP(
            self.settings.smtp_host,
            self.settings.smtp_port,
            timeout=15,
        ) as smtp:
            smtp.ehlo()
            if self.settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(self.settings.smtp_username, password)
            smtp.send_message(message)


def get_email_sender(settings: Settings = Depends(get_settings)) -> EmailSender:
    return EmailSender(settings)
