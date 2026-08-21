from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.routes import financial_mode
from app.auth import AuthContext, require_auth
from app.database import get_db
from app.services.cashflow import build_cashflow


router = APIRouter(prefix="/api/cashflow", tags=["cash flow"])


@router.get("")
def cashflow(
    history_days: int = Query(60, ge=30, le=365),
    forecast_days: int = Query(30, ge=7, le=90),
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    mode = financial_mode(db, context.business.id)
    return build_cashflow(
        db,
        business_id=context.business.id,
        mode=mode,
        history_days=history_days,
        forecast_days=forecast_days,
    )
