import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import settings


def _database_path() -> Path:
    if not settings.database_url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// database URLs are supported in this MVP")
    return Path(settings.database_url.replace("sqlite:///", "", 1))


@contextmanager
def get_db():
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                phone TEXT NOT NULL,
                language TEXT NOT NULL,
                stripe_connected_account_id TEXT,
                reliability REAL NOT NULL,
                seeded_price INTEGER,
                seeded_delivery_hours INTEGER,
                seeded_response TEXT NOT NULL,
                in_stock INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        _add_column_if_missing(db, "suppliers", "stripe_connected_account_id", "TEXT")
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS negotiation_runs (
                id TEXT PRIMARY KEY,
                request_text TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                item TEXT NOT NULL,
                destination TEXT NOT NULL,
                budget INTEGER NOT NULL,
                needed_by TEXT NOT NULL,
                status TEXT NOT NULL,
                winner_supplier_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                supplier_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                price INTEGER,
                delivery_hours INTEGER,
                reliability REAL NOT NULL,
                message TEXT NOT NULL,
                score REAL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(run_id) REFERENCES negotiation_runs(id),
                FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                supplier_id INTEGER NOT NULL,
                stripe_checkout_session_id TEXT UNIQUE,
                stripe_payment_intent_id TEXT,
                stripe_transfer_id TEXT,
                amount INTEGER NOT NULL,
                application_fee_amount INTEGER NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(run_id) REFERENCES negotiation_runs(id),
                FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
            )
            """
        )
        _add_column_if_missing(db, "transactions", "stripe_transfer_id", "TEXT")
        seed_suppliers(db)


def _add_column_if_missing(
    db: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_type: str,
) -> None:
    columns = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    if any(column["name"] == column_name for column in columns):
        return
    db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def seed_suppliers(db: sqlite3.Connection) -> None:
    count = db.execute("SELECT COUNT(*) AS count FROM suppliers").fetchone()["count"]
    if count:
        _backfill_connected_accounts(db)
        return

    suppliers = [
        (
            1,
            "Zambales Hardware",
            "Iba, Zambales",
            "+63 917 100 1001",
            "Tagalog",
            settings.stripe_supplier_1_account_id,
            0.96,
            7500,
            8,
            "Sige, PHP 7,500 na lang, kasama na delivery.",
            1,
        ),
        (
            2,
            "Olongapo Builders Supply",
            "Olongapo City",
            "+63 917 100 1002",
            "Taglish",
            settings.stripe_supplier_2_account_id,
            0.91,
            7800,
            18,
            "We can do PHP 7,800 and deliver Friday morning.",
            1,
        ),
        (
            3,
            "Subic Cement Co.",
            "Subic Bay",
            "+63 917 100 1003",
            "English",
            settings.stripe_supplier_3_account_id,
            0.87,
            8200,
            14,
            "PHP 8,200 is our best including delivery.",
            1,
        ),
        (
            4,
            "Bataan Trading",
            "Balanga, Bataan",
            "+63 917 100 1004",
            "Tagalog",
            settings.stripe_supplier_4_account_id,
            0.78,
            None,
            None,
            "Wala kaming stock ngayon, sir. Restock next week.",
            0,
        ),
        (
            5,
            "Iba Construction Mart",
            "Iba, Zambales",
            "+63 917 100 1005",
            "Taglish",
            settings.stripe_supplier_5_account_id,
            0.84,
            7900,
            10,
            "PHP 7,900, kaya namin Friday afternoon.",
            1,
        ),
    ]
    db.executemany(
        """
        INSERT INTO suppliers (
            id, name, location, phone, language, reliability, seeded_price,
            seeded_delivery_hours, seeded_response, in_stock, stripe_connected_account_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                supplier[0],
                supplier[1],
                supplier[2],
                supplier[3],
                supplier[4],
                supplier[6],
                supplier[7],
                supplier[8],
                supplier[9],
                supplier[10],
                supplier[5],
            )
            for supplier in suppliers
        ],
    )


def _backfill_connected_accounts(db: sqlite3.Connection) -> None:
    accounts = {
        1: settings.stripe_supplier_1_account_id,
        2: settings.stripe_supplier_2_account_id,
        3: settings.stripe_supplier_3_account_id,
        4: settings.stripe_supplier_4_account_id,
        5: settings.stripe_supplier_5_account_id,
    }
    db.executemany(
        """
        UPDATE suppliers
        SET stripe_connected_account_id = ?
        WHERE id = ?
        """,
        [(account_id, supplier_id) for supplier_id, account_id in accounts.items()],
    )
