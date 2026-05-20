import asyncio
import sqlite3
import uuid
from dataclasses import dataclass

from app.database import get_db
from app.models import Decision, DemoRequest, Quote, RunSnapshot


@dataclass
class ConnectionManager:
    active: dict[str, set] 

    def __init__(self) -> None:
        self.active = {}

    async def connect(self, run_id: str, websocket) -> None:
        await websocket.accept()
        self.active.setdefault(run_id, set()).add(websocket)

    def disconnect(self, run_id: str, websocket) -> None:
        sockets = self.active.get(run_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self.active.pop(run_id, None)

    async def broadcast(self, run_id: str, snapshot: RunSnapshot) -> None:
        sockets = list(self.active.get(run_id, set()))
        for websocket in sockets:
            try:
                await websocket.send_json(snapshot.model_dump())
            except RuntimeError:
                self.disconnect(run_id, websocket)


manager = ConnectionManager()


def create_run(request: DemoRequest) -> RunSnapshot:
    run_id = str(uuid.uuid4())
    with get_db() as db:
        db.execute(
            """
            INSERT INTO negotiation_runs (
                id, request_text, quantity, item, destination, budget, needed_by, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                request.request_text,
                request.quantity,
                request.item,
                request.destination,
                request.budget,
                request.needed_by,
                "running",
            ),
        )
        suppliers = db.execute("SELECT * FROM suppliers ORDER BY id").fetchall()
        db.executemany(
            """
            INSERT INTO quotes (
                run_id, supplier_id, status, price, delivery_hours, reliability, message, score
            )
            VALUES (?, ?, 'queued', NULL, NULL, ?, 'Queued for supplier call.', NULL)
            """,
            [(run_id, supplier["id"], supplier["reliability"]) for supplier in suppliers],
        )
    return get_snapshot(run_id)


def get_snapshot(run_id: str) -> RunSnapshot:
    with get_db() as db:
        run = db.execute("SELECT * FROM negotiation_runs WHERE id = ?", (run_id,)).fetchone()
        if not run:
            raise KeyError(run_id)

        quote_rows = db.execute(
            """
            SELECT q.*, s.name AS supplier_name, s.location, s.language
            FROM quotes q
            JOIN suppliers s ON s.id = q.supplier_id
            WHERE q.run_id = ?
            ORDER BY s.id
            """,
            (run_id,),
        ).fetchall()
        quotes = [_quote_from_row(row) for row in quote_rows]
        decision = _decision_from_rows(db, run_id)
        request = DemoRequest(
            request_text=run["request_text"],
            quantity=run["quantity"],
            item=run["item"],
            destination=run["destination"],
            budget=run["budget"],
            needed_by=run["needed_by"],
        )
        return RunSnapshot(
            run_id=run_id,
            request=request,
            status=run["status"],
            quotes=quotes,
            decision=decision,
        )


async def run_simulation(run_id: str) -> None:
    with get_db() as db:
        suppliers = db.execute("SELECT * FROM suppliers ORDER BY id").fetchall()
    await asyncio.gather(*[_simulate_supplier(run_id, dict(supplier)) for supplier in suppliers])
    _choose_winner(run_id)
    await manager.broadcast(run_id, get_snapshot(run_id))


async def _simulate_supplier(run_id: str, supplier: dict) -> None:
    await _update_quote(run_id, supplier["id"], "ringing", None, None, "Dialing supplier...")
    await asyncio.sleep(0.35 + supplier["id"] * 0.2)
    await _update_quote(
        run_id,
        supplier["id"],
        "talking",
        None,
        None,
        f"Agent connected in {supplier['language']}. Confirming stock and delivery window.",
    )
    await asyncio.sleep(0.8 + supplier["id"] * 0.15)

    if not supplier["in_stock"]:
        await _update_quote(
            run_id,
            supplier["id"],
            "out_of_stock",
            None,
            None,
            supplier["seeded_response"],
        )
        return

    score = score_quote(
        supplier["seeded_price"],
        supplier["seeded_delivery_hours"],
        supplier["reliability"],
    )
    await _update_quote(
        run_id,
        supplier["id"],
        "closed",
        supplier["seeded_price"],
        supplier["seeded_delivery_hours"],
        supplier["seeded_response"],
        score,
    )


async def _update_quote(
    run_id: str,
    supplier_id: int,
    status: str,
    price: int | None,
    delivery_hours: int | None,
    message: str,
    score: float | None = None,
) -> None:
    with get_db() as db:
        db.execute(
            """
            UPDATE quotes
            SET status = ?, price = ?, delivery_hours = ?, message = ?, score = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE run_id = ? AND supplier_id = ?
            """,
            (status, price, delivery_hours, message, score, run_id, supplier_id),
        )
    await manager.broadcast(run_id, get_snapshot(run_id))


def score_quote(price: int, delivery_hours: int, reliability: float) -> float:
    price_score = max(0, 1 - ((price - 7000) / 2500))
    delivery_score = max(0, 1 - (delivery_hours / 48))
    return round((price_score * 0.5) + (delivery_score * 0.25) + (reliability * 0.25), 4)


def _choose_winner(run_id: str) -> None:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT * FROM quotes
            WHERE run_id = ? AND status = 'closed' AND price IS NOT NULL
            ORDER BY score DESC, price ASC, delivery_hours ASC
            """,
            (run_id,),
        ).fetchall()
        if not rows:
            db.execute("UPDATE negotiation_runs SET status = 'complete' WHERE id = ?", (run_id,))
            return
        winner = rows[0]
        db.execute(
            """
            UPDATE negotiation_runs
            SET status = 'complete', winner_supplier_id = ?
            WHERE id = ?
            """,
            (winner["supplier_id"], run_id),
        )


def _decision_from_rows(db: sqlite3.Connection, run_id: str) -> Decision | None:
    row = db.execute(
        """
        SELECT q.*, s.name AS supplier_name
        FROM quotes q
        JOIN negotiation_runs r ON r.winner_supplier_id = q.supplier_id AND r.id = q.run_id
        JOIN suppliers s ON s.id = q.supplier_id
        WHERE q.run_id = ?
        """,
        (run_id,),
    ).fetchone()
    if not row or row["price"] is None or row["delivery_hours"] is None or row["score"] is None:
        return None

    return Decision(
        supplier_id=row["supplier_id"],
        supplier_name=row["supplier_name"],
        price=row["price"],
        delivery_hours=row["delivery_hours"],
        reliability=row["reliability"],
        score=row["score"],
        reason="Best blended score across price, delivery speed, and supplier reliability.",
    )


def _quote_from_row(row: sqlite3.Row) -> Quote:
    return Quote(
        supplier_id=row["supplier_id"],
        supplier_name=row["supplier_name"],
        location=row["location"],
        language=row["language"],
        status=row["status"],
        price=row["price"],
        delivery_hours=row["delivery_hours"],
        reliability=row["reliability"],
        message=row["message"],
        score=row["score"],
    )
