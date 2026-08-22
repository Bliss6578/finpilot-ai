from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.routes import financial_mode
from app.auth import AuthContext, require_auth, require_frontend_request
from app.database import get_db
from app.models import ApprovalRequest, CFOConversation, CFOMessage, Expense, FinancialAlert
from app.services.financial_engine import financial_summary, rebuild_daily_metrics, refresh_anomaly_alerts
from app.services.scenarios import simulate


router = APIRouter(prefix="/api/v1", tags=["financial intelligence"])


class BusinessProfileUpdate(BaseModel):
    industry: Optional[str] = Field(default=None, max_length=120)
    website: Optional[HttpUrl] = None
    current_cash: Optional[float] = Field(default=None, ge=0)
    monthly_budget: Optional[float] = Field(default=None, ge=0)
    monthly_fixed_expenses: Optional[float] = Field(default=None, ge=0)
    minimum_reserve: Optional[float] = Field(default=None, ge=0)
    target_runway_months: Optional[float] = Field(default=None, ge=1, le=60)
    target_growth_rate: Optional[float] = Field(default=None, ge=-100, le=1000)
    risk_tolerance: Optional[Literal["conservative", "moderate", "aggressive"]] = None


class ExpenseCreate(BaseModel):
    category: str = Field(min_length=2, max_length=80)
    description: Optional[str] = Field(default=None, max_length=500)
    amount: float = Field(gt=0)
    expense_type: Literal["operating", "payroll", "tax", "vendor", "capital", "other"] = "operating"
    recurring: bool = False
    expense_date: date


class ScenarioRequest(BaseModel):
    type: Literal["new_hire", "marketing", "revenue_change", "expense_reduction", "custom"]
    parameters: dict[str, float] = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]


def require_owner(context: AuthContext) -> None:
    if context.membership.role != "owner":
        raise HTTPException(status_code=403, detail="Only a business owner can change financial controls")


def _money(value: Optional[int]) -> Optional[float]:
    return None if value is None else round(value / 100, 2)


@router.get("/settings/business-profile")
def get_business_profile(context: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    business = context.business
    return {
        "name": business.name, "currency": business.currency, "industry": business.industry,
        "website": business.website, "current_cash": _money(business.current_cash_paise),
        "monthly_budget": _money(business.monthly_budget_paise),
        "monthly_fixed_expenses": _money(business.monthly_fixed_expenses_paise),
        "minimum_reserve": _money(business.minimum_reserve_paise),
        "target_runway_months": business.target_runway_months,
        "target_growth_rate": business.target_growth_rate, "risk_tolerance": business.risk_tolerance,
    }


@router.put("/settings/business-profile")
def update_business_profile(
    payload: BusinessProfileUpdate,
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_frontend_request),
) -> dict[str, Any]:
    require_owner(context)
    data = payload.model_dump(exclude_unset=True)
    for field in ("current_cash", "monthly_budget", "monthly_fixed_expenses", "minimum_reserve"):
        if field in data:
            setattr(context.business, f"{field}_paise", None if data[field] is None else round(data[field] * 100))
    for field in ("industry", "target_runway_months", "target_growth_rate", "risk_tolerance"):
        if field in data:
            setattr(context.business, field, data[field])
    if "website" in data:
        context.business.website = str(data["website"]) if data["website"] else None
    db.commit()
    return get_business_profile(context)


@router.get("/expenses")
def list_expenses(
    limit: int = Query(100, ge=1, le=500),
    context: AuthContext = Depends(require_auth), db: Session = Depends(get_db),
) -> dict[str, Any]:
    items = db.scalars(select(Expense).where(Expense.business_id == context.business.id).order_by(desc(Expense.expense_date)).limit(limit)).all()
    return {"items": [{"id": item.id, "category": item.category, "description": item.description, "amount": _money(item.amount_paise), "expense_type": item.expense_type, "recurring": item.recurring, "expense_date": item.expense_date.isoformat()} for item in items], "total": len(items)}


@router.post("/expenses", status_code=201)
def create_expense(
    payload: ExpenseCreate, context: AuthContext = Depends(require_auth), db: Session = Depends(get_db),
    _: None = Depends(require_frontend_request),
) -> dict[str, Any]:
    expense = Expense(id=str(uuid4()), business_id=context.business.id, category=payload.category.strip(), description=payload.description, amount_paise=round(payload.amount * 100), expense_type=payload.expense_type, recurring=payload.recurring, expense_date=payload.expense_date)
    db.add(expense)
    db.commit()
    return {"id": expense.id, "created": True}


@router.delete("/expenses/{expense_id}")
def delete_expense(
    expense_id: str, context: AuthContext = Depends(require_auth), db: Session = Depends(get_db),
    _: None = Depends(require_frontend_request),
) -> dict[str, bool]:
    item = db.scalar(select(Expense).where(Expense.id == expense_id, Expense.business_id == context.business.id))
    if item is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}


@router.get("/dashboard/summary")
def dashboard_summary(
    days: int = Query(30, ge=7, le=365), context: AuthContext = Depends(require_auth), db: Session = Depends(get_db),
) -> dict[str, Any]:
    return financial_summary(db, context.business.id, financial_mode(db, context.business.id), days)


@router.get("/dashboard/health")
def dashboard_health(context: AuthContext = Depends(require_auth), db: Session = Depends(get_db)) -> dict[str, Any]:
    return financial_summary(db, context.business.id, financial_mode(db, context.business.id), 30)["health"]


@router.get("/forecast/cashflow")
def forecast_cashflow(
    horizon_days: int = Query(30, ge=7, le=90), context: AuthContext = Depends(require_auth), db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = financial_summary(db, context.business.id, financial_mode(db, context.business.id), 30)["forecast"]
    points = [point for point in result["points"] if point["kind"] == "forecast"][:horizon_days]
    return {**result, "points": points, "horizon_days": horizon_days}


@router.post("/scenarios/simulate")
def simulate_scenario(
    payload: ScenarioRequest, context: AuthContext = Depends(require_auth), db: Session = Depends(get_db),
    _: None = Depends(require_frontend_request),
) -> dict[str, Any]:
    summary = financial_summary(db, context.business.id, financial_mode(db, context.business.id), 30)
    try:
        return simulate(summary, payload.type, payload.parameters)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/alerts")
def list_alerts(
    refresh: bool = False, context: AuthContext = Depends(require_auth), db: Session = Depends(get_db),
) -> dict[str, Any]:
    mode = financial_mode(db, context.business.id)
    if refresh:
        rebuild_daily_metrics(db, context.business.id, mode)
        refresh_anomaly_alerts(db, context.business.id, mode)
        db.commit()
    items = db.scalars(select(FinancialAlert).where(FinancialAlert.business_id == context.business.id, FinancialAlert.mode == mode).order_by(desc(FinancialAlert.created_at)).limit(100)).all()
    return {"items": [{"id": item.id, "type": item.alert_type, "severity": item.severity, "title": item.title, "description": item.description, "metric_value": item.metric_value, "baseline_value": item.baseline_value, "status": item.status, "evidence": item.evidence, "created_at": item.created_at.isoformat()} for item in items], "unread": sum(item.status == "unread" for item in items)}


@router.patch("/alerts/{alert_id}")
def mark_alert_read(
    alert_id: str, context: AuthContext = Depends(require_auth), db: Session = Depends(get_db),
    _: None = Depends(require_frontend_request),
) -> dict[str, str]:
    item = db.scalar(select(FinancialAlert).where(FinancialAlert.id == alert_id, FinancialAlert.business_id == context.business.id))
    if item is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    item.status = "read"
    db.commit()
    return {"status": "read"}


@router.get("/cfo/conversations")
def list_conversations(context: AuthContext = Depends(require_auth), db: Session = Depends(get_db)) -> dict[str, Any]:
    items = db.scalars(select(CFOConversation).where(CFOConversation.business_id == context.business.id).order_by(desc(CFOConversation.updated_at)).limit(50)).all()
    return {"items": [{"id": item.id, "title": item.title, "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat()} for item in items]}


@router.get("/cfo/conversations/{conversation_id}")
def get_conversation(conversation_id: str, context: AuthContext = Depends(require_auth), db: Session = Depends(get_db)) -> dict[str, Any]:
    conversation = db.scalar(select(CFOConversation).where(CFOConversation.id == conversation_id, CFOConversation.business_id == context.business.id))
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = db.scalars(select(CFOMessage).where(CFOMessage.conversation_id == conversation.id).order_by(CFOMessage.created_at)).all()
    return {"id": conversation.id, "title": conversation.title, "messages": [{"id": item.id, "role": item.role, "content": item.content, "structured_content": item.structured_content, "created_at": item.created_at.isoformat()} for item in messages]}


@router.get("/approvals")
def list_approvals(context: AuthContext = Depends(require_auth), db: Session = Depends(get_db)) -> dict[str, Any]:
    items = db.scalars(select(ApprovalRequest).where(ApprovalRequest.business_id == context.business.id).order_by(desc(ApprovalRequest.created_at))).all()
    return {"items": [{"id": item.id, "action_type": item.action_type, "title": item.title, "parameters": item.parameters, "status": item.status, "created_at": item.created_at.isoformat()} for item in items]}


@router.post("/approvals/{approval_id}/decision")
def decide_approval(
    approval_id: str, payload: ApprovalDecision, context: AuthContext = Depends(require_auth), db: Session = Depends(get_db),
    _: None = Depends(require_frontend_request),
) -> dict[str, Any]:
    require_owner(context)
    item = db.scalar(select(ApprovalRequest).where(ApprovalRequest.id == approval_id, ApprovalRequest.business_id == context.business.id))
    if item is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="Approval request is already resolved")
    item.status = payload.decision
    item.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": item.id, "status": item.status, "executed": False, "note": "Approval is recorded; no financial action is executed automatically."}
