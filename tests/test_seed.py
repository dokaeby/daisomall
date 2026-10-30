from __future__ import annotations

from app.db import connect
from app.seed import seed


def test_seed_is_idempotent(app):
    seed(app.state.settings)
    seed(app.state.settings)

    conn = connect(app.state.db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 24
        assert conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1").fetchone()[0] == 1
    finally:
        conn.close()


def test_seeded_catalog_is_browsable(client):
    from app.seed import seed

    seed(client.app.state.settings)
    res = client.get("/")
    assert res.status_code == 200
    assert res.text.count('class="card"') == 12
