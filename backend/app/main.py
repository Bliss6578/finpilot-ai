from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.auth import router as auth_router
from app.api.razorpay_oauth import router as razorpay_oauth_router
from app.api.razorpay_keys import router as razorpay_keys_router
from app.api.cashflow import router as cashflow_router
from app.api.ai_cfo import router as ai_cfo_router, v1_router as ai_cfo_v1_router
from app.api.financial_intelligence import router as financial_intelligence_router
from app.config import get_settings

settings = get_settings()
app = FastAPI(title="FinPilot API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
app.include_router(auth_router)
app.include_router(razorpay_oauth_router)
app.include_router(razorpay_keys_router)
app.include_router(cashflow_router)
app.include_router(ai_cfo_router)
app.include_router(ai_cfo_v1_router)
app.include_router(financial_intelligence_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "FinPilot API", "docs": "/docs", "health": "/api/health"}
