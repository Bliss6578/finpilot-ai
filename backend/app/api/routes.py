from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.auth import AuthContext, require_auth, require_frontend_request
from app.database import SessionLocal, get_db
from app.models import RazorpayConnection, Refund, Settlement, SyncRun, Transaction, WebhookEvent
from app.security import decrypt_secret
from app.services.razorpay import (
    RazorpayService,
    refresh_oauth_connection,
    upsert_payment,
    upsert_refund,
    upsert_settlement,
    verify_webhook_signature,
)
from app.services.financial_engine import rebuild_daily_metrics, refresh_anomaly_alerts

router = APIRouter(prefix="/api")
logger = logging.getLogger("paymentor.ingestion")


def financial_mode(db: Session, business_id: str) -> str:
    connection = db.scalar(
        select(RazorpayConnection).where(RazorpayConnection.business_id == business_id)
    )
    return connection.mode if connection and connection.status == "connected" else "test"


def transaction_json(item: Transaction) -> dict[str, Any]:
    return {
        "id": item.razorpay_payment_id,
        "order_id": item.razorpay_order_id,
        "customer": item.customer_name or "Razorpay customer",
        "email": item.customer_email,
        "amount": item.amount_paise / 100,
        "currency": item.currency,
        "method": item.method,
        "status": item.status,
        "fee": item.fee_paise / 100,
        "tax": item.tax_paise / 100,
        "date": item.provider_created_at.isoformat(),
        "mode": item.mode,
    }


def refund_json(item: Refund) -> dict[str, Any]:
    return {
        "id": item.razorpay_refund_id,
        "payment_id": item.razorpay_payment_id,
        "amount": item.amount_paise / 100,
        "currency": item.currency,
        "status": item.status,
        "receipt": item.receipt,
        "speed_requested": item.speed_requested,
        "speed_processed": item.speed_processed,
        "arn": item.arn,
        "date": item.provider_created_at.isoformat(),
        "mode": item.mode,
    }


def settlement_json(item: Settlement) -> dict[str, Any]:
    return {
        "id": item.razorpay_settlement_id,
        "amount": item.amount_paise / 100,
        "status": item.status,
        "fees": item.fees_paise / 100,
        "tax": item.tax_paise / 100,
        "utr": item.utr,
        "date": item.provider_created_at.isoformat(),
        "mode": item.mode,
    }


@router.get("/health")
def health(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    db.execute(select(1))
    return {
        "status": "ok",
        "environment": settings.app_env,
        "database": "ok",
        "razorpay_configured": settings.razorpay_configured,
    }


@router.get("/razorpay/status")
def razorpay_status(
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    connection = db.scalar(
        select(RazorpayConnection).where(RazorpayConnection.business_id == context.business.id)
    )
    latest = db.scalar(
        select(SyncRun)
        .where(
            SyncRun.business_id == context.business.id,
            SyncRun.mode == (connection.mode if connection else "test"),
        )
        .order_by(desc(SyncRun.started_at))
        .limit(1)
    )
    return {
        "connected": bool(connection and connection.status == "connected"),
        "mode": connection.mode if connection else "test",
        "connection_type": connection.auth_type if connection else None,
        "api_key_id": connection.api_key_id if connection and connection.auth_type == "api_key" else None,
        "webhook_url": (
            f"{settings.backend_origin}/api/webhooks/razorpay/{connection.webhook_token}"
            if connection and connection.auth_type == "api_key" and connection.webhook_token
            else None
        ),
        "oauth_available": settings.razorpay_oauth_configured,
        "last_sync": latest.finished_at.isoformat() if latest and latest.finished_at else None,
        "last_sync_status": latest.status if latest else "never",
    }


@router.post("/razorpay/sync")
async def sync_razorpay(
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_frontend_request),
) -> dict[str, Any]:
    connection = db.scalar(
        select(RazorpayConnection).where(
            RazorpayConnection.business_id == context.business.id,
            RazorpayConnection.status == "connected",
        )
    )
    if connection is None:
        raise HTTPException(status_code=409, detail="Connect this business to Razorpay first")
    run = SyncRun(business_id=context.business.id, mode=connection.mode, status="running")
    db.add(run)
    db.commit()
    logger.info("razorpay_sync_started", extra={"business_id": context.business.id, "mode": connection.mode})
    try:
        connection = await refresh_oauth_connection(db, settings, connection)
        service = RazorpayService(settings, connection)
        payments = await service.fetch_payments()
        warnings: list[str] = []
        try:
            refunds = await service.fetch_refunds()
        except (httpx.HTTPError, ValueError):
            refunds = []
            warnings.append(f"Refund history is unavailable for this Razorpay {connection.mode.title()} account")
        try:
            settlements = await service.fetch_settlements()
        except (httpx.HTTPError, ValueError):
            settlements = []
            warnings.append(f"Settlement history is unavailable for this Razorpay {connection.mode.title()} account")
        for payment in payments:
            upsert_payment(db, payment, context.business.id, connection.mode)
        for refund in refunds:
            upsert_refund(db, refund, context.business.id, connection.mode)
        for settlement in settlements:
            upsert_settlement(db, settlement, context.business.id, connection.mode)
        rebuild_daily_metrics(db, context.business.id, connection.mode)
        refresh_anomaly_alerts(db, context.business.id, connection.mode)
        records_processed = len(payments) + len(refunds) + len(settlements)
        run.status = "completed"
        run.records_processed = records_processed
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("razorpay_sync_completed", extra={"business_id": context.business.id, "mode": connection.mode, "records_processed": records_processed})
        return {
            "success": True,
            "records_processed": records_processed,
            "records": {
                "payments": len(payments),
                "refunds": len(refunds),
                "settlements": len(settlements),
            },
            "warnings": warnings,
            "synced_at": run.finished_at.isoformat(),
        }
    except (httpx.HTTPError, ValueError) as exc:
        run.status = "failed"
        run.error_message = str(exc)[:500]
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=502, detail=f"Unable to synchronize Razorpay {connection.mode} data") from exc


@router.get("/transactions")
def list_transactions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    days: int = Query(30, ge=1, le=365),
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    mode = financial_mode(db, context.business.id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filters = (
        Transaction.business_id == context.business.id,
        Transaction.mode == mode,
        Transaction.provider_created_at >= cutoff,
    )
    items = db.scalars(
        select(Transaction)
        .where(*filters)
        .order_by(desc(Transaction.provider_created_at))
        .offset(offset)
        .limit(limit)
    ).all()
    total = db.scalar(
        select(func.count()).select_from(Transaction).where(*filters)
    ) or 0
    return {"items": [transaction_json(item) for item in items], "total": total, "limit": limit, "offset": offset, "mode": mode}


@router.get("/transactions/{payment_id}")
def get_transaction(
    payment_id: str,
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    mode = financial_mode(db, context.business.id)
    item = db.scalar(
        select(Transaction).where(
            Transaction.business_id == context.business.id,
            Transaction.mode == mode,
            Transaction.razorpay_payment_id == payment_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction_json(item)


@router.get("/refunds")
def list_refunds(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    mode = financial_mode(db, context.business.id)
    tenant = (Refund.business_id == context.business.id, Refund.mode == mode)
    items = db.scalars(
        select(Refund).where(*tenant).order_by(desc(Refund.provider_created_at)).offset(offset).limit(limit)
    ).all()
    total = db.scalar(select(func.count()).select_from(Refund).where(*tenant)) or 0
    return {"items": [refund_json(item) for item in items], "total": total, "limit": limit, "offset": offset, "mode": mode}


@router.get("/refunds/{refund_id}")
def get_refund(
    refund_id: str,
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    mode = financial_mode(db, context.business.id)
    item = db.scalar(
        select(Refund).where(
            Refund.business_id == context.business.id,
            Refund.mode == mode,
            Refund.razorpay_refund_id == refund_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Refund not found")
    return refund_json(item)


@router.get("/settlements")
def list_settlements(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    mode = financial_mode(db, context.business.id)
    tenant = (Settlement.business_id == context.business.id, Settlement.mode == mode)
    items = db.scalars(
        select(Settlement)
        .where(*tenant)
        .order_by(desc(Settlement.provider_created_at))
        .offset(offset)
        .limit(limit)
    ).all()
    total = db.scalar(select(func.count()).select_from(Settlement).where(*tenant)) or 0
    return {
        "items": [settlement_json(item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
        "mode": mode,
    }


@router.get("/settlements/{settlement_id}")
def get_settlement(
    settlement_id: str,
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    mode = financial_mode(db, context.business.id)
    item = db.scalar(
        select(Settlement).where(
            Settlement.business_id == context.business.id,
            Settlement.mode == mode,
            Settlement.razorpay_settlement_id == settlement_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return settlement_json(item)


@router.get("/dashboard")
def dashboard(
    days: int = Query(30, ge=1, le=365),
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    mode = financial_mode(db, context.business.id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    tenant = (
        Transaction.business_id == context.business.id,
        Transaction.mode == mode,
        Transaction.provider_created_at >= cutoff,
    )
    revenue = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount_paise), 0)).where(*tenant, Transaction.status == "captured")
    ) or 0
    total = db.scalar(select(func.count()).select_from(Transaction).where(*tenant)) or 0
    captured = db.scalar(
        select(func.count()).select_from(Transaction).where(*tenant, Transaction.status == "captured")
    ) or 0
    failed = db.scalar(
        select(func.count()).select_from(Transaction).where(*tenant, Transaction.status == "failed")
    ) or 0
    payment_fees = db.scalar(
        select(func.coalesce(func.sum(Transaction.fee_paise), 0)).where(*tenant, Transaction.status == "captured")
    ) or 0
    refund_tenant = (
        Refund.business_id == context.business.id,
        Refund.mode == mode,
        Refund.provider_created_at >= cutoff,
    )
    refunded = db.scalar(
        select(func.count()).select_from(Refund).where(*refund_tenant, Refund.status == "processed")
    ) or 0
    refund_amount = db.scalar(
        select(func.coalesce(func.sum(Refund.amount_paise), 0)).where(
            *refund_tenant,
            Refund.status == "processed",
        )
    ) or 0
    pending_refund_amount = db.scalar(
        select(func.coalesce(func.sum(Refund.amount_paise), 0)).where(
            *refund_tenant,
            Refund.status == "pending",
        )
    ) or 0
    settlement_tenant = (
        Settlement.business_id == context.business.id,
        Settlement.mode == mode,
        Settlement.provider_created_at >= cutoff,
    )
    settled_amount = db.scalar(
        select(func.coalesce(func.sum(Settlement.amount_paise), 0)).where(
            *settlement_tenant,
            Settlement.status == "processed",
        )
    ) or 0
    pending_settlements = db.scalar(
        select(func.count()).select_from(Settlement).where(
            *settlement_tenant,
            Settlement.status == "created",
        )
    ) or 0
    completed_settlements = db.scalar(
        select(func.count()).select_from(Settlement).where(
            *settlement_tenant,
            Settlement.status == "processed",
        )
    ) or 0
    failed_settlements = db.scalar(
        select(func.count()).select_from(Settlement).where(
            *settlement_tenant,
            Settlement.status == "failed",
        )
    ) or 0
    recent = db.scalars(
        select(Transaction).where(*tenant).order_by(desc(Transaction.provider_created_at)).limit(5)
    ).all()
    success_rate = round(captured / total * 100, 1) if total else 0
    net_revenue = revenue - refund_amount - payment_fees
    return {
        "revenue": float(revenue) / 100,
        "payment_success_rate": success_rate,
        "transaction_counts": {
            "total": total,
            "captured": captured,
            "failed": failed,
            "refunded": refunded,
        },
        "financial_summary": {
            "gross_revenue": float(revenue) / 100,
            "refund_amount": float(refund_amount) / 100,
            "pending_refund_amount": float(pending_refund_amount) / 100,
            "razorpay_fees": float(payment_fees) / 100,
            "net_revenue": float(net_revenue) / 100,
            "settled_amount": float(settled_amount) / 100,
        },
        "settlement_counts": {
            "pending": pending_settlements,
            "completed": completed_settlements,
            "failed": failed_settlements,
        },
        "recent_transactions": [transaction_json(item) for item in recent],
        "data_source": "razorpay" if total else "empty",
        "mode": mode,
    }


def process_webhook(event_id: int) -> None:
    with SessionLocal() as db:
        event = db.get(WebhookEvent, event_id)
        if event is None or event.status == "processed":
            return
        try:
            payment = event.payload.get("payload", {}).get("payment", {}).get("entity")
            refund = event.payload.get("payload", {}).get("refund", {}).get("entity")
            settlement = event.payload.get("payload", {}).get("settlement", {}).get("entity")
            if payment:
                upsert_payment(db, payment, event.business_id, event.mode)
            if refund:
                upsert_refund(db, refund, event.business_id, event.mode)
            if settlement:
                upsert_settlement(db, settlement, event.business_id, event.mode)
            rebuild_daily_metrics(db, event.business_id, event.mode)
            created_alerts = refresh_anomaly_alerts(db, event.business_id, event.mode)
            event.status = "processed"
            event.processed_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("webhook_processed", extra={"business_id": event.business_id, "event_type": event.event_type, "alerts_created": len(created_alerts)})
        except Exception as exc:
            event.status = "failed"
            event.error_message = str(exc)[:500]
            db.commit()


def accept_webhook(
    db: Session,
    background_tasks: BackgroundTasks,
    connection: RazorpayConnection,
    payload: dict[str, Any],
    provider_event_id: str,
) -> dict[str, bool]:
    existing = db.scalar(
        select(WebhookEvent).where(
            WebhookEvent.business_id == connection.business_id,
            WebhookEvent.mode == connection.mode,
            WebhookEvent.provider_event_id == provider_event_id,
        )
    )
    if existing:
        return {"accepted": True, "duplicate": True}
    event = WebhookEvent(
        business_id=connection.business_id,
        mode=connection.mode,
        provider_event_id=provider_event_id,
        event_type=payload.get("event", "unknown"),
        payload=payload,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    background_tasks.add_task(process_webhook, event.id)
    return {"accepted": True, "duplicate": False}


@router.post("/webhooks/razorpay/{webhook_token}", status_code=status.HTTP_202_ACCEPTED)
async def razorpay_tenant_webhook(
    webhook_token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    x_razorpay_signature: str = Header(default=""),
    x_razorpay_event_id: str = Header(default=""),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
    connection = db.scalar(
        select(RazorpayConnection).where(
            RazorpayConnection.webhook_token == webhook_token,
            RazorpayConnection.auth_type == "api_key",
            RazorpayConnection.status == "connected",
        )
    )
    if connection is None or not connection.webhook_secret_encrypted:
        raise HTTPException(status_code=404, detail="Webhook connection not found")
    if not x_razorpay_event_id:
        raise HTTPException(status_code=400, detail="Missing Razorpay event identifier")
    raw_body = await request.body()
    try:
        webhook_secret = decrypt_secret(connection.webhook_secret_encrypted, settings.token_encryption_key)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="Webhook verification is unavailable") from exc
    if not verify_webhook_signature(raw_body, x_razorpay_signature, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
    return accept_webhook(db, background_tasks, connection, payload, x_razorpay_event_id)


@router.post("/webhooks/razorpay", status_code=status.HTTP_202_ACCEPTED)
async def razorpay_webhook(request: Request, background_tasks: BackgroundTasks, x_razorpay_signature: str = Header(default=""), x_razorpay_event_id: str = Header(default=""), db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    raw_body = await request.body()
    if not verify_webhook_signature(raw_body, x_razorpay_signature, settings.razorpay_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    if not x_razorpay_event_id:
        raise HTTPException(status_code=400, detail="Missing Razorpay event identifier")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
    account_id = payload.get("account_id")
    connection = None
    if account_id:
        connection = db.scalar(
            select(RazorpayConnection).where(
                RazorpayConnection.razorpay_account_id == account_id,
                RazorpayConnection.status == "connected",
            )
        )
    if connection is None:
        connections = db.scalars(
            select(RazorpayConnection).where(
                RazorpayConnection.status == "connected",
                RazorpayConnection.auth_type != "api_key",
            ).limit(2)
        ).all()
        if len(connections) == 1:
            connection = connections[0]
    if connection is None:
        raise HTTPException(status_code=400, detail="Webhook account is not connected to Paymentor")
    return accept_webhook(db, background_tasks, connection, payload, x_razorpay_event_id)
