from typing import Literal

from pydantic import BaseModel


class Supplier(BaseModel):
    id: int
    name: str
    location: str
    phone: str
    language: str
    stripe_connected_account_id: str | None = None
    reliability: float
    in_stock: bool


class DemoRequest(BaseModel):
    request_text: str = "I need 20 bags of cement delivered to Zambales by Friday, budget 8,000."
    quantity: int = 20
    item: str = "cement bags"
    destination: str = "Zambales"
    budget: int = 8000
    needed_by: str = "Friday"


class Quote(BaseModel):
    supplier_id: int
    supplier_name: str
    location: str
    language: str
    status: Literal["queued", "ringing", "talking", "closed", "out_of_stock"]
    price: int | None = None
    delivery_hours: int | None = None
    reliability: float
    message: str
    score: float | None = None


class Decision(BaseModel):
    supplier_id: int
    supplier_name: str
    price: int
    delivery_hours: int
    reliability: float
    score: float
    reason: str


class RunSnapshot(BaseModel):
    run_id: str
    request: DemoRequest
    status: Literal["running", "complete"]
    quotes: list[Quote]
    decision: Decision | None = None


class CheckoutRequest(BaseModel):
    run_id: str


class CheckoutSession(BaseModel):
    transaction_id: str
    checkout_session_id: str
    checkout_url: str
    provider: str
    mode: Literal["test"]
    amount: int
    application_fee_amount: int
    currency: str
    status: str


class Transaction(BaseModel):
    id: str
    run_id: str
    supplier_id: int
    stripe_checkout_session_id: str | None = None
    stripe_payment_intent_id: str | None = None
    stripe_transfer_id: str | None = None
    amount: int
    application_fee_amount: int
    currency: str
    status: str
