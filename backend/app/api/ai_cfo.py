from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes import financial_mode
from app.auth import AuthContext, require_auth, require_frontend_request
from app.database import get_db
from app.services.ai_cfo import answer_cfo_question, build_cfo_context


router = APIRouter(prefix="/api/ai-cfo", tags=["AI CFO"])


class CFOQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=600)


@router.get("/context")
def cfo_context(
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    mode = financial_mode(db, context.business.id)
    result = build_cfo_context(db, context.business.id, mode)
    current = result["current"]
    cashflow = result["cashflow"]
    return {
        "as_of": result["as_of"],
        "mode": mode,
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
    _: None = Depends(require_frontend_request),
) -> dict[str, Any]:
    mode = financial_mode(db, context.business.id)
    return answer_cfo_question(db, context.business.id, mode, payload.question.strip())
