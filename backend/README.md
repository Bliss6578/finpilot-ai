# FinPilot API

FastAPI backend for Razorpay synchronization, finance metrics, and webhook ingestion.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for the interactive API documentation.

Run `alembic upgrade head` before starting the API. PostgreSQL is recommended for all shared environments.

## Multi-tenant accounts

FinPilot uses secure, HTTP-only session cookies. The first account created in a development database becomes the owner of the migrated `demo-business` workspace so existing Razorpay records are preserved. Later sign-ups receive isolated business workspaces.

Razorpay connections for client workspaces use Partner OAuth with read-only access, encrypted tokens, refresh-token rotation, and server-side revocation. Configure `RAZORPAY_CLIENT_ID`, `RAZORPAY_CLIENT_SECRET`, `RAZORPAY_REDIRECT_URI`, `RAZORPAY_OAUTH_MODE`, and a Fernet `TOKEN_ENCRYPTION_KEY` after registering a development application in the Razorpay Partner Dashboard.
