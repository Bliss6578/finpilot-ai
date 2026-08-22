from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes import financial_mode
from app.auth import AuthContext, require_auth, require_frontend_request
from app.config import Settings, get_settings
from app.database import get_db
from app.models import CFOConversation, CFOMessage, RazorpayConnection
from app.services.ai_cfo import answer_cfo_question, build_cfo_context
from app.services.financial_engine import financial_summary
from app.services.finance_agent import run_finpilot_agent


router = APIRouter(prefix="/api/ai-cfo", tags=["AI CFO"])
v1_router = APIRouter(prefix="/api/v1/cfo", tags=["AI CFO"])


class CFOQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=600)
    conversation_id: Optional[str] = None


class CFOChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=600)
    conversation_id: Optional[str] = None


def _razorpay_connection(db: Session, business_id: str) -> RazorpayConnection | None:
    return db.scalar(select(RazorpayConnection).where(
        RazorpayConnection.business_id == business_id,
        RazorpayConnection.status == "connected",
    ))


def _connection_required_result(mode: str) -> dict[str, Any]:
    return {
        "answer": "Please connect your Razorpay to continue.",
        "recommendation": "Open Settings and connect this workspace's Razorpay account.",
        "classification": "fact",
        "metrics": [],
        "insights": [],
        "actions": [{"label": "Connect Razorpay", "action": "open_settings"}],
        "tools_used": ["check_razorpay_connection"],
        "engine": "finpilot_access_policy",
        "suggestions": [],
        "evidence": {
            "tenant_scope": "authenticated_workspace",
            "mode": mode,
            "period_days": 30,
            "latest_data_at": None,
            "cashflow_source": "workspace_financial_records",
            "sources": [],
        },
    }


def _answer_and_store(db: Session, context: AuthContext, question: str, conversation_id: Optional[str], settings: Settings) -> dict[str, Any]:
    conversation = None
    if conversation_id:
        conversation = db.scalar(select(CFOConversation).where(
            CFOConversation.id == conversation_id,
            CFOConversation.business_id == context.business.id,
        ))
        if conversation is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation is None:
        conversation = CFOConversation(id=str(uuid4()), business_id=context.business.id, title=question[:80])
        db.add(conversation)
        db.flush()
    prior_messages = list(db.scalars(
        select(CFOMessage).where(CFOMessage.conversation_id == conversation.id).order_by(CFOMessage.created_at.desc()).limit(6)
    ).all())
    history = [{"role": item.role, "content": item.content} for item in reversed(prior_messages)]
    db.add(CFOMessage(id=str(uuid4()), conversation_id=conversation.id, role="user", content=question, structured_content={}))
    connection = _razorpay_connection(db, context.business.id)
    if connection is None:
        result = _connection_required_result("test")
        result["conversation_id"] = conversation.id
        db.add(CFOMessage(id=str(uuid4()), conversation_id=conversation.id, role="assistant", content=result["answer"], structured_content=result))
        db.commit()
        return result
    mode = financial_mode(db, context.business.id)
    result = run_finpilot_agent(db, context.business.id, mode, question)
    result["conversation_id"] = conversation.id
    db.add(CFOMessage(id=str(uuid4()), conversation_id=conversation.id, role="assistant", content=result["answer"], structured_content=result))
    db.commit()
    return result


@router.get("/context")
def cfo_context(
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    connection = _razorpay_connection(db, context.business.id)
    if connection is None:
        return {
            "as_of": None,
            "mode": "test",
            "razorpay_connected": False,
            "latest_data_at": None,
            "payment_attempts": 0,
            "suggestions": [],
            "focus": {
                "title": "Connect Razorpay",
                "description": "Connect this workspace's Razorpay account to activate the AI CFO.",
                "cashflow_source": "workspace_financial_records",
            },
        }
    mode = financial_mode(db, context.business.id)
    result = build_cfo_context(db, context.business.id, mode)
    current = result["current"]
    cashflow = result["cashflow"]
    return {
        "as_of": result["as_of"],
        "mode": mode,
        "razorpay_connected": True,
        "latest_data_at": result["latest_data_at"],
        "payment_attempts": current.attempts,
        "suggestions": result["suggestions"],
        "focus": {
            "title": "Cash buffer integrity" if cashflow["summary"]["risk_level"] != "low" else "Payment proceeds and reserves",
            "description": f"30-day modeled close ₹{cashflow['summary']['forecast_closing_balance']:,.0f}; {cashflow['summary']['risk_level']} reserve risk.",
            "cashflow_source": cashflow["data_source"],
        },
    }


@router.post("/ask")
def ask_cfo(
    payload: CFOQuestion,
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_frontend_request),
) -> dict[str, Any]:
    return _answer_and_store(db, context, payload.question.strip(), payload.conversation_id, settings)


@v1_router.post("/chat")
def cfo_chat(
    payload: CFOChatRequest,
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_frontend_request),
) -> dict[str, Any]:
    return _answer_and_store(db, context, payload.message.strip(), payload.conversation_id, settings)


@v1_router.get("/briefing")
def cfo_briefing(
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    mode = financial_mode(db, context.business.id)
    summary = financial_summary(db, context.business.id, mode, 30)
    current = summary["current"]
    changes = summary["changes"]
    risks: list[str] = []
    if changes["failure_rate_points"] > 1:
        risks.append(f"Payment failure rate increased by {changes['failure_rate_points']:.1f} percentage points.")
    if changes["refund_rate_points"] > 1:
        risks.append(f"Refund rate increased by {changes['refund_rate_points']:.1f} percentage points.")
    if current["net_cashflow_paise"] < 0:
        risks.append("Verified net cash flow is negative for this period.")
    if not summary["data_completeness"]["expenses"]:
        risks.append("Expense data is incomplete, so profit and runway are not verified.")
    wins: list[str] = []
    growth = changes["net_revenue_percent"]
    if growth is not None and growth > 0:
        wins.append(f"Net payment revenue increased {growth:.1f}% from the previous period.")
    if current["failure_rate"] < 5 and current["attempts"]:
        wins.append(f"Payment failure rate is contained at {current['failure_rate']:.1f}%.")
    return {
        "title": "FinPilot weekly CFO brief",
        "as_of": summary["as_of"],
        "health": summary["health"],
        "revenue": {"net": current["net_revenue_paise"] / 100, "growth_percent": growth},
        "cashflow": {"net": current["net_cashflow_paise"] / 100, "runway_months": summary["cash"]["runway_months"]},
        "wins": wins or ["No verified positive trend is strong enough to highlight yet."],
        "risks": risks or ["No material risk threshold is currently breached."],
        "priorities": ["Complete missing cash and expense data", "Review payment and refund anomalies", "Run important spending decisions through Scenario Lab"],
    }
