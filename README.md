# FinPilot AI

FinPilot is a private-beta finance intelligence workspace for businesses using Razorpay. It combines a React/Vite frontend with a FastAPI backend and PostgreSQL.

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

FinPilot includes an explainable demo prior trained from the UCI Online Retail II dataset. The committed JSON artifact contains only aggregate seasonality and return-rate parameters; the 45 MB source workbook is not committed or loaded by the production API.

To reproduce the artifact locally:

```bash
cd backend
pip install -r requirements-training.txt
python scripts/train_retail_cashflow.py /absolute/path/to/online+retail+ii.zip
pytest -q
```

The dataset teaches sales seasonality and cancellation behavior. It does not contain bank balances or operating expenses, so INR scale, opening cash, fixed expenses, variable costs, payment fees, and safe reserve are disclosed synthetic demo assumptions. Synced Razorpay activity appears immediately; the dataset fills missing history until 14 active workspace days are available, after which the workspace history supplies the personalized sales baseline.

Source: https://archive.ics.uci.edu/dataset/502/online+retail+ii

## Grounded AI CFO

`POST /api/ai-cfo/ask` calculates answers from the authenticated business and its active Test/Live mode. It compares the latest 30 days with the preceding 30 days across payments, refunds, Razorpay fees, settlements, and the FinPilot cash-flow model. Responses include their evidence sources and contextual follow-up questions.

The CFO deliberately calls Razorpay-derived revenue “net payment proceeds,” not accounting profit. It will not invent causes involving advertising, payroll, inventory, tax, or products until those data sources are connected. Tenant-isolation tests verify that one business cannot appear in another business's answer.

## Deployment

The frontend is configured for Vercel. Set `VITE_API_URL` to the deployed HTTPS backend URL before publishing authenticated functionality. Backend secrets must be configured only in the hosting provider's encrypted environment-variable settings.
