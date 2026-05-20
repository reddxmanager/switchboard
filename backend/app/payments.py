import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any

import stripe

from app.config import settings
from app.database import get_db
from app.models import CheckoutSession, Decision

CURRENCY = "php"
logger = logging.getLogger(__name__)


class PaymentProvider(ABC):
    @abstractmethod
    def create_checkout_session(
        self,
        run_id: str,
        decision: Decision,
        connected_account_id: str,
    ) -> CheckoutSession:
        raise NotImplementedError


class StripeTestPaymentProvider(PaymentProvider):
    def create_checkout_session(
        self,
        run_id: str,
        decision: Decision,
        connected_account_id: str,
    ) -> CheckoutSession:
        if not settings.stripe_secret_key:
            raise PaymentConfigurationError("STRIPE_SECRET_KEY is required")
        if not connected_account_id:
            raise PaymentConfigurationError("Winning supplier is missing a Stripe connected account ID")

        stripe.api_key = settings.stripe_secret_key
        amount = decision.price * 100
        application_fee_amount = calculate_platform_fee(amount)
        transaction_id = str(uuid.uuid4())

        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=settings.stripe_success_url,
            cancel_url=settings.stripe_cancel_url,
            client_reference_id=run_id,
            line_items=[
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": CURRENCY,
                        "unit_amount": amount,
                        "product_data": {
                            "name": f"{decision.supplier_name} supplier payment",
                            "description": "20 bags cement delivered to Zambales",
                        },
                    },
                }
            ],
            payment_intent_data={
                "metadata": {
                    "transaction_id": transaction_id,
                    "run_id": run_id,
                    "supplier_id": str(decision.supplier_id),
                },
            },
            metadata={
                "transaction_id": transaction_id,
                "run_id": run_id,
                "supplier_id": str(decision.supplier_id),
            },
        )

        checkout_session_id = _stripe_value(session, "id")
        checkout_url = _stripe_value(session, "url")
        if not checkout_session_id or not checkout_url:
            raise PaymentProviderError("Stripe did not return a Checkout Session URL")

        with get_db() as db:
            db.execute(
                """
                INSERT INTO transactions (
                    id, run_id, supplier_id, stripe_checkout_session_id, amount,
                    application_fee_amount, currency, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction_id,
                    run_id,
                    decision.supplier_id,
                    checkout_session_id,
                    amount,
                    application_fee_amount,
                    CURRENCY,
                    "checkout_created",
                ),
            )

        return CheckoutSession(
            transaction_id=transaction_id,
            checkout_session_id=checkout_session_id,
            checkout_url=checkout_url,
            provider="stripe",
            mode="test",
            amount=amount,
            application_fee_amount=application_fee_amount,
            currency=CURRENCY,
            status="checkout_created",
        )


class PaymentConfigurationError(RuntimeError):
    pass


class PaymentProviderError(RuntimeError):
    pass


def calculate_platform_fee(amount: int) -> int:
    return round(amount * settings.stripe_platform_fee_bps / 10_000)


def mark_checkout_completed(session: Any) -> str | None:
    checkout_session_id = _stripe_value(session, "id")
    payment_intent_id = _stripe_value(session, "payment_intent")
    metadata = _stripe_value(session, "metadata") or {}
    transaction_id = metadata.get("transaction_id")
    should_transfer = False

    with get_db() as db:
        if transaction_id:
            db.execute(
                """
                UPDATE transactions
                SET status = 'paid',
                    stripe_payment_intent_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (payment_intent_id, transaction_id),
            )
            should_transfer = True

        elif checkout_session_id:
            db.execute(
                """
                UPDATE transactions
                SET status = 'paid',
                    stripe_payment_intent_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE stripe_checkout_session_id = ?
                """,
                (payment_intent_id, checkout_session_id),
            )
    if should_transfer and transaction_id:
        try:
            transfer_to_supplier(transaction_id)
        except Exception:
            logger.exception("Could not transfer paid transaction %s to supplier", transaction_id)
    return transaction_id


def transfer_to_supplier(transaction_id: str) -> str | None:
    if not settings.stripe_secret_key:
        raise PaymentConfigurationError("STRIPE_SECRET_KEY is required")

    with get_db() as db:
        transaction = db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (transaction_id,),
        ).fetchone()
        if transaction is None:
            return None

        supplier = db.execute(
            "SELECT stripe_connected_account_id FROM suppliers WHERE id = ?",
            (transaction["supplier_id"],),
        ).fetchone()
        if supplier is None:
            raise PaymentProviderError("Transaction supplier was not found")
        connected_account_id = supplier["stripe_connected_account_id"]
        if not connected_account_id:
            raise PaymentConfigurationError("Transaction supplier is missing a Stripe connected account ID")

        transfer_amount = transaction["amount"] - transaction["application_fee_amount"]
        if transfer_amount <= 0:
            raise PaymentProviderError("Transfer amount must be greater than zero")

        stripe.api_key = settings.stripe_secret_key
        transfer = stripe.Transfer.create(
            amount=transfer_amount,
            currency=CURRENCY,
            destination=connected_account_id,
            transfer_group=transaction_id,
            metadata={
                "transaction_id": transaction_id,
                "run_id": transaction["run_id"],
                "supplier_id": str(transaction["supplier_id"]),
            },
        )
        transfer_id = _stripe_value(transfer, "id")
        if not transfer_id:
            raise PaymentProviderError("Stripe did not return a Transfer ID")

        db.execute(
            """
            UPDATE transactions
            SET stripe_transfer_id = ?,
                status = 'paid_and_transferred',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (transfer_id, transaction_id),
        )
        return transfer_id


def construct_webhook_event(payload: bytes, signature: str | None) -> Any:
    if not settings.stripe_webhook_secret:
        raise PaymentConfigurationError("STRIPE_WEBHOOK_SECRET is required")
    if not signature:
        raise PaymentProviderError("Missing Stripe-Signature header")
    return stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)


def _stripe_value(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


payment_provider: PaymentProvider = StripeTestPaymentProvider()
