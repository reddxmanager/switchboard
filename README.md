# Sourcer

Sourcer is a local MVP for a multi-agent supplier negotiation dashboard. The demo runs simulated parallel supplier calls, streams live updates over WebSocket, chooses a winning supplier by price, delivery speed, and reliability, then creates a Stripe test-mode Checkout Session behind a `PaymentProvider` interface.

Core demo prompt:

```text
I need 20 bags of cement delivered to Zambales by Friday, budget 8,000.
```

## Stack

- React + Vite + TypeScript frontend
- FastAPI backend
- SQLite database with seeded suppliers
- WebSocket live negotiation updates
- Stripe test-mode Checkout with Connect destination charges

## Local Setup

1. Create environment files:

```bash
copy .env.example .env
```

2. Install and run the backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

3. Install and run the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

4. Open the dashboard:

```text
http://localhost:5173
```

The frontend automatically starts the cement sourcing demo. Use `Run demo` to restart the simulation.

## Required Env Vars

Backend:

- `DATABASE_URL`: SQLite URL. Default: `sqlite:///./sourcer.db`.
- `FRONTEND_ORIGIN`: Allowed browser origin for CORS. Default: `http://localhost:5173`.
- `STRIPE_SECRET_KEY`: Stripe test secret key, for example `sk_test_...`.
- `STRIPE_WEBHOOK_SECRET`: Stripe webhook signing secret from `stripe listen` or the Stripe Dashboard, for example `whsec_...`.
- `STRIPE_SUCCESS_URL`: Checkout success redirect URL. Include `{CHECKOUT_SESSION_ID}` if you want Stripe to inject the session ID.
- `STRIPE_CANCEL_URL`: Checkout cancel redirect URL.
- `STRIPE_PLATFORM_FEE_BPS`: Platform cut in basis points. `300` means 3%.
- `STRIPE_SUPPLIER_1_ACCOUNT_ID`: Stripe test connected account ID for Zambales Hardware.
- `STRIPE_SUPPLIER_2_ACCOUNT_ID`: Stripe test connected account ID for Olongapo Builders Supply.
- `STRIPE_SUPPLIER_3_ACCOUNT_ID`: Stripe test connected account ID for Subic Cement Co.
- `STRIPE_SUPPLIER_4_ACCOUNT_ID`: Stripe test connected account ID for Bataan Trading.
- `STRIPE_SUPPLIER_5_ACCOUNT_ID`: Stripe test connected account ID for Iba Construction Mart.

Frontend:

- `VITE_API_BASE_URL`: Backend API base URL. Default: `http://localhost:8000`.

Seeded suppliers include connected account IDs in SQLite via `stripe_connected_account_id`. For a real Stripe test-mode Checkout flow, create or use test connected accounts under your Stripe platform account and place those `acct_...` values in the `STRIPE_SUPPLIER_*_ACCOUNT_ID` env vars. On backend startup, existing seeded rows are updated from those env vars, so you do not need to delete `sourcer.db` after changing them.

## Stripe Webhooks

Run the backend, then forward Stripe test events locally:

```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
```

Copy the printed `whsec_...` value into `STRIPE_WEBHOOK_SECRET`.

The webhook handler listens for `checkout.session.completed` and updates the matching SQLite transaction to `paid`.

## Checks

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm run build
```

## API

- `GET /health` returns backend health.
- `GET /suppliers` lists seeded suppliers.
- `POST /negotiations` starts a simulated negotiation run.
- `GET /negotiations/{run_id}` returns the latest snapshot.
- `WS /ws/negotiations/{run_id}` streams live quote updates.
- `POST /checkout` creates a Stripe test-mode Checkout Session for the winner.
- `GET /transactions/{transaction_id}` returns a persisted payment transaction.
- `POST /webhooks/stripe` handles Stripe webhook events.

## Provider Boundaries

No ElevenLabs or Twilio integrations are included yet. Supplier calls are simulated in `backend/app/negotiation.py`.

Payments are routed through `backend/app/payments.py`:

- `PaymentProvider` defines the interface.
- `StripeTestPaymentProvider` creates a test-mode Checkout Session.

Checkout uses the winning supplier's connected account ID, adds `payment_intent_data.application_fee_amount` for the platform cut, and sends the remaining funds to the supplier with `payment_intent_data.transfer_data.destination`.
"# switchboard" 
