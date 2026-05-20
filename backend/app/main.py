import asyncio

import stripe
from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import get_db, init_db
from app.models import (
    CheckoutRequest,
    CheckoutSession,
    DemoRequest,
    RunSnapshot,
    Supplier,
    Transaction,
)
from app.negotiation import create_run, get_snapshot, manager, run_simulation
from app.payments import (
    PaymentConfigurationError,
    PaymentProviderError,
    construct_webhook_event,
    mark_checkout_completed,
    payment_provider,
)

app = FastAPI(title="Sourcer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/suppliers", response_model=list[Supplier])
def suppliers() -> list[Supplier]:
    with get_db() as db:
        rows = db.execute("SELECT * FROM suppliers ORDER BY id").fetchall()
    return [
        Supplier(
            id=row["id"],
            name=row["name"],
            location=row["location"],
            phone=row["phone"],
            language=row["language"],
            stripe_connected_account_id=row["stripe_connected_account_id"],
            reliability=row["reliability"],
            in_stock=bool(row["in_stock"]),
        )
        for row in rows
    ]


@app.post("/negotiations", response_model=RunSnapshot)
async def start_negotiation(request: DemoRequest) -> RunSnapshot:
    snapshot = create_run(request)
    asyncio.create_task(run_simulation(snapshot.run_id))
    return snapshot


@app.get("/negotiations/{run_id}", response_model=RunSnapshot)
def read_negotiation(run_id: str) -> RunSnapshot:
    try:
        return get_snapshot(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Negotiation not found") from exc


@app.post("/checkout", response_model=CheckoutSession)
def checkout(payload: CheckoutRequest) -> CheckoutSession:
    try:
        snapshot = get_snapshot(payload.run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Negotiation not found") from exc
    if snapshot.decision is None:
        raise HTTPException(status_code=409, detail="No winning supplier yet")
    connected_account_id = _connected_account_for_supplier(snapshot.decision.supplier_id)
    try:
        return payment_provider.create_checkout_session(
            payload.run_id,
            snapshot.decision,
            connected_account_id,
        )
    except PaymentConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail=f"Stripe error: {exc.user_message or str(exc)}") from exc
    except PaymentProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/transactions/{transaction_id}", response_model=Transaction)
def read_transaction(transaction_id: str) -> Transaction:
    with get_db() as db:
        row = db.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return Transaction(**dict(row))


@app.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, bool | str | None]:
    payload = await request.body()
    try:
        event = construct_webhook_event(payload, stripe_signature)
    except PaymentConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (PaymentProviderError, ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if event["type"] == "checkout.session.completed":
        transaction_id = mark_checkout_completed(event["data"]["object"])
        return {"received": True, "transaction_id": transaction_id}

    return {"received": True, "transaction_id": None}


@app.websocket("/ws/negotiations/{run_id}")
async def negotiation_socket(websocket: WebSocket, run_id: str) -> None:
    await manager.connect(run_id, websocket)
    try:
        await websocket.send_json(get_snapshot(run_id).model_dump())
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, KeyError):
        manager.disconnect(run_id, websocket)


def _connected_account_for_supplier(supplier_id: int) -> str:
    with get_db() as db:
        row = db.execute(
            "SELECT stripe_connected_account_id FROM suppliers WHERE id = ?",
            (supplier_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Winning supplier not found")
    connected_account_id = row["stripe_connected_account_id"]
    if not connected_account_id:
        raise HTTPException(status_code=409, detail="Winning supplier has no Stripe connected account")
    return connected_account_id
