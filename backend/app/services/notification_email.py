"""Preference-aware, privacy-preserving workspace email notifications."""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Business, BusinessMember, FinancialAlert, User
from app.services.email import EmailSender

logger = logging.getLogger("paymentor.notifications")

ALERT_PREFERENCES = {
    "payment_failure_spike": "Payment failures",
    "refund_spike": "Refund spikes",
    "cash_flow_risk": "Cash flow risks",
    "settlement_delay": "Settlement changes",
    "settlement_mismatch": "Settlement changes",
    "unusual_transaction": "Unusual transactions",
}


def send_financial_alert_emails(business_id: str, alert_ids: list[str]) -> None:
    """Notify verified members without putting financial evidence into email."""
    if not alert_ids:
        return
    settings = get_settings()
    if not settings.email_configured:
        return
    try:
        with SessionLocal() as db:
            business = db.get(Business, business_id)
            if business is None:
                return
            preferences = business.notification_preferences or {}
            alert_types = set(db.scalars(select(FinancialAlert.alert_type).where(
                FinancialAlert.business_id == business_id,
                FinancialAlert.id.in_(alert_ids),
            )).all())
            enabled_categories = {
                category for alert_type in alert_types
                if (category := ALERT_PREFERENCES.get(alert_type)) and preferences.get(category, True)
            }
            if not enabled_categories:
                return
            recipients = list(db.scalars(
                select(User)
                .join(BusinessMember, BusinessMember.user_id == User.id)
                .where(
                    BusinessMember.business_id == business_id,
                    User.is_active.is_(True),
                    User.email_verified.is_(True),
                )
            ).all())
            sender = EmailSender(settings)
            for category in enabled_categories:
                for user in recipients:
                    sender.send_notification(
                        to=user.email,
                        name=user.full_name,
                        category=category,
                        url=f"{settings.frontend_origin}/alerts",
                    )
    except Exception:
        logger.exception("financial_alert_email_failed", extra={"business_id": business_id})
