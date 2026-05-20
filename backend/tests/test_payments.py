from types import SimpleNamespace

from app.config import settings
from app.database import get_db, init_db
from app.models import Decision
from app.payments import StripeTestPaymentProvider, mark_checkout_completed


def configure_test_db(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'sourcer-test.db'}")
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_local")
    monkeypatch.setattr(settings, "stripe_platform_fee_bps", 300)
    monkeypatch.setattr(settings, "stripe_supplier_1_account_id", "acct_test_supplier_1")
    init_db()


def test_seeded_supplier_connected_account_comes_from_env(monkeypatch, tmp_path) -> None:
    configure_test_db(monkeypatch, tmp_path)

    with get_db() as db:
        row = db.execute(
            "SELECT stripe_connected_account_id FROM suppliers WHERE id = 1",
        ).fetchone()

    assert row["stripe_connected_account_id"] == "acct_test_supplier_1"


def test_checkout_session_uses_separate_charge_without_transfer_data(
    monkeypatch,
    tmp_path,
) -> None:
    configure_test_db(monkeypatch, tmp_path)
    captured: dict = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="cs_test_123", url="https://checkout.stripe.test/session")

    monkeypatch.setattr("app.payments.stripe.checkout.Session.create", fake_create)

    result = StripeTestPaymentProvider().create_checkout_session(
        run_id="run_123",
        connected_account_id="acct_test_supplier_1",
        decision=Decision(
            supplier_id=1,
            supplier_name="Zambales Hardware",
            price=7500,
            delivery_hours=8,
            reliability=0.96,
            score=0.8483,
            reason="Best blended offer.",
        ),
    )

    assert result.checkout_session_id == "cs_test_123"
    assert result.amount == 750000
    assert result.application_fee_amount == 22500
    assert "application_fee_amount" not in captured["payment_intent_data"]
    assert "transfer_data" not in captured["payment_intent_data"]
    assert captured["metadata"]["transaction_id"] == result.transaction_id

    with get_db() as db:
        row = db.execute("SELECT * FROM transactions WHERE id = ?", (result.transaction_id,)).fetchone()

    assert row["stripe_checkout_session_id"] == "cs_test_123"
    assert row["status"] == "checkout_created"


def test_checkout_completed_webhook_marks_transaction_paid(monkeypatch, tmp_path) -> None:
    configure_test_db(monkeypatch, tmp_path)
    transaction_id = "txn_test_123"
    captured_transfer: dict = {}

    def fake_transfer_create(**kwargs):
        captured_transfer.update(kwargs)
        return SimpleNamespace(id="tr_test_123")

    monkeypatch.setattr("app.payments.stripe.Transfer.create", fake_transfer_create)

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
                "run_123",
                1,
                "cs_test_123",
                750000,
                22500,
                "php",
                "checkout_created",
            ),
        )

    returned_id = mark_checkout_completed(
        {
            "id": "cs_test_123",
            "payment_intent": "pi_test_123",
            "metadata": {"transaction_id": transaction_id},
        },
    )

    with get_db() as db:
        row = db.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()

    assert returned_id == transaction_id
    assert row["status"] == "paid_and_transferred"
    assert row["stripe_payment_intent_id"] == "pi_test_123"
    assert row["stripe_transfer_id"] == "tr_test_123"
    assert captured_transfer["amount"] == 727500
    assert captured_transfer["currency"] == "php"
    assert captured_transfer["destination"] == "acct_test_supplier_1"
    assert captured_transfer["transfer_group"] == transaction_id
    assert captured_transfer["metadata"]["transaction_id"] == transaction_id
