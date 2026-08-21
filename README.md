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

## Deployment

The frontend is configured for Vercel. Set `VITE_API_URL` to the deployed HTTPS backend URL before publishing authenticated functionality. Backend secrets must be configured only in the hosting provider's encrypted environment-variable settings.

