from app.negotiation import score_quote


def test_score_prefers_strong_blended_offer() -> None:
    zambales = score_quote(price=7500, delivery_hours=8, reliability=0.96)
    subic = score_quote(price=8200, delivery_hours=14, reliability=0.87)

    assert zambales > subic
    assert zambales == 0.8483
