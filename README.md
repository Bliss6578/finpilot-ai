# Paymentor

Paymentor is a private-beta finance intelligence workspace for businesses using Razorpay. It combines a React/Vite frontend with a FastAPI backend and PostgreSQL.

## Project structure

- `frontend/` — public website, authentication, dashboard, and finance workspace
- `backend/` — API, authentication, Razorpay sync/webhooks, PostgreSQL models, and migrations

## Local development

Copy each `.env.example` file to its local `.env` equivalent and supply your own credentials. Never commit Razorpay secrets, database passwords, JWT secrets, or webhook secrets.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Dataset-backed cash-flow model

Paymentor includes an explainable demo prior trained from the UCI Online Retail II dataset. The committed JSON artifact contains only aggregate seasonality and return-rate parameters; the 45 MB source workbook is not committed or loaded by the production API.

To reproduce the artifact locally:

```bash
cd backend
pip install -r requirements-training.txt
python scripts/train_retail_cashflow.py /absolute/path/to/online+retail+ii.zip
pytest -q
```

The dataset teaches sales seasonality and cancellation behavior. It does not contain bank balances or operating expenses, so INR scale, opening cash, fixed expenses, variable costs, payment fees, and safe reserve are disclosed synthetic demo assumptions. Synced Razorpay activity appears immediately; the dataset fills missing history until 14 active workspace days are available, after which the workspace history supplies the personalized sales baseline.

Source: https://archive.ics.uci.edu/dataset/502/online+retail+ii

## FinQA symbolic reasoning router

Paymentor can learn finance-question operation patterns from FinQA without using
the source reports as client evidence. Build the compact artifact locally:

```bash
cd backend
python scripts/prepare_finqa_reasoning.py /path/to/archive.zip
```

The generated artifact retains only normalized questions and symbolic operation
names. All client amounts continue to come from that authenticated workspace's
database and deterministic financial tools.

## Grounded AI CFO

`POST /api/v1/cfo/chat` calculates answers from the authenticated business and its active Test/Live mode. Conversations and structured answers persist per workspace. It compares the latest 30 days with the preceding 30 days across payments, refunds, Razorpay fees, settlements, recorded expenses, cash policy, and the FinPilot cash-flow model. Responses identify the deterministic tools used, evidence sources, classifications, recommended actions, and contextual follow-up questions.

The CFO deliberately calls Razorpay-derived revenue “net payment proceeds,” not accounting profit. It will not invent causes involving advertising, payroll, inventory, tax, or products until those data sources are connected. Tenant-isolation tests verify that one business cannot appear in another business's answer.

## Financial intelligence platform

Run `alembic upgrade head` after pulling. The financial-intelligence migration adds business memory, expense records, daily metrics, anomaly alerts, CFO conversations, forecast snapshots, and approval requests.

Important authenticated endpoints:

- `GET /api/v1/dashboard/summary` — deterministic revenue, cash flow, burn, runway, completeness, forecast, and health score
- `GET|PUT /api/v1/settings/business-profile` — current cash, reserve, fixed expenses, risk tolerance, and planning targets
- `GET|POST|DELETE /api/v1/expenses` — tenant-scoped operating expense ledger
- `POST /api/v1/scenarios/simulate` — deterministic what-if results without LLM arithmetic
- `GET /api/v1/alerts?refresh=true` — rolling payment/refund anomaly detection
- `POST /api/v1/cfo/chat` and `GET /api/v1/cfo/briefing` — persistent grounded CFO analysis
- `GET /api/v1/approvals` — approval records; no financial action executes automatically

Seed a realistic six-month demo workspace, including expenses, settlements and one payment anomaly:

```bash
cd backend
python scripts/seed_demo_company.py --business-id YOUR_BUSINESS_ID --payments 5000
```

All tenant identifiers come from the authenticated server-side session. API clients never submit a business ID, and financial credentials remain backend-only.

## Deployment

The frontend is configured for Vercel. Set `VITE_API_URL` to the deployed HTTPS backend URL before publishing authenticated functionality. Backend secrets must be configured only in the hosting provider's encrypted environment-variable settings.
