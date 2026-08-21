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

The dataset teaches sales seasonality and cancellation behavior. It does not contain bank balances or operating expenses, so INR scale, opening cash, fixed expenses, variable costs, payment fees, and safe reserve are disclosed synthetic demo assumptions. After a workspace has at least 14 active Razorpay transaction days, its own isolated history supplies the sales baseline while the public artifact continues to provide seasonality.

Source: https://archive.ics.uci.edu/dataset/502/online+retail+ii

## Deployment

The frontend is configured for Vercel. Set `VITE_API_URL` to the deployed HTTPS backend URL before publishing authenticated functionality. Backend secrets must be configured only in the hosting provider's encrypted environment-variable settings.
