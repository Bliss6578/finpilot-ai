from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.auth import AuthContext, require_auth, require_frontend_request
from app.database import SessionLocal, get_db
from app.models import RazorpayConnection, SyncRun, Transaction, WebhookEvent
from app.services.razorpay import (
    RazorpayService,
    refresh_oauth_connection,
    upsert_payment,
    verify_webhook_signature,
)

router = APIRouter(prefix="/api")


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
        .where(SyncRun.business_id == context.business.id)
        .order_by(desc(SyncRun.started_at))
        .limit(1)
    )
    return {
        "connected": bool(connection and connection.status == "connected"),
        "mode": connection.mode if connection else "test",
        "connection_type": connection.auth_type if connection else None,
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
    run = SyncRun(business_id=context.business.id, status="running")
    db.add(run)
    db.commit()
    try:
        connection = await refresh_oauth_connection(db, settings, connection)
        payments = await RazorpayService(settings, connection).fetch_payments()
        for payment in payments:
            upsert_payment(db, payment, context.business.id)
        run.status = "completed"
        run.records_processed = len(payments)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        return {"success": True, "records_processed": len(payments), "synced_at": run.finished_at.isoformat()}
    except (httpx.HTTPError, ValueError) as exc:
        run.status = "failed"
        run.error_message = str(exc)[:500]
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=502, detail="Unable to synchronize Razorpay test data") from exc


@router.get("/transactions")
def list_transactions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    items = db.scalars(
        select(Transaction)
        .where(Transaction.business_id == context.business.id)
        .order_by(desc(Transaction.provider_created_at))
        .offset(offset)
        .limit(limit)
    ).all()
    total = db.scalar(
        select(func.count()).select_from(Transaction).where(Transaction.business_id == context.business.id)
    ) or 0
    return {"items": [transaction_json(item) for item in items], "total": total, "limit": limit, "offset": offset}


@router.get("/transactions/{payment_id}")
def get_transaction(
    payment_id: str,
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    item = db.scalar(
        select(Transaction).where(
            Transaction.business_id == context.business.id,
            Transaction.razorpay_payment_id == payment_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction_json(item)


@router.get("/dashboard")
def dashboard(
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    tenant = Transaction.business_id == context.business.id
    revenue = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount_paise), 0)).where(tenant, Transaction.status == "captured")
    ) or 0
    total = db.scalar(select(func.count()).select_from(Transaction).where(tenant)) or 0
    captured = db.scalar(
        select(func.count()).select_from(Transaction).where(tenant, Transaction.status == "captured")
    ) or 0
    failed = db.scalar(
        select(func.count()).select_from(Transaction).where(tenant, Transaction.status == "failed")
    ) or 0
    refunded = db.scalar(
        select(func.count()).select_from(Transaction).where(tenant, Transaction.status == "refunded")
    ) or 0
    recent = db.scalars(
        select(Transaction).where(tenant).order_by(desc(Transaction.provider_created_at)).limit(5)
    ).all()
    success_rate = round(captured / total * 100, 1) if total else 0
    return {"revenue": float(revenue) / 100, "payment_success_rate": success_rate, "transaction_counts": {"total": total, "captured": captured, "failed": failed, "refunded": refunded}, "recent_transactions": [transaction_json(item) for item in recent], "data_source": "razorpay" if total else "empty"}


def process_webhook(event_id: int) -> None:
    with SessionLocal() as db:
        event = db.get(WebhookEvent, event_id)
        if event is None or event.status == "processed":
            return
        try:
            payment = event.payload.get("payload", {}).get("payment", {}).get("entity")
            if payment:
                upsert_payment(db, payment, event.business_id)
            event.status = "processed"
            event.processed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as exc:
            event.status = "failed"
            event.error_message = str(exc)[:500]
            db.commit()


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
            select(RazorpayConnection).where(RazorpayConnection.status == "connected").limit(2)
        ).all()
        if len(connections) == 1:
            connection = connections[0]
    if connection is None:
        raise HTTPException(status_code=400, detail="Webhook account is not connected to FinPilot")
    existing = db.scalar(
        select(WebhookEvent).where(
            WebhookEvent.business_id == connection.business_id,
            WebhookEvent.provider_event_id == x_razorpay_event_id,
        )
    )
    if existing:
        return {"accepted": True, "duplicate": True}
    event = WebhookEvent(
        business_id=connection.business_id,
        provider_event_id=x_razorpay_event_id,
        event_type=payload.get("event", "unknown"),
        payload=payload,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    background_tasks.add_task(process_webhook, event.id)
    return {"accepted": True, "duplicate": False}
