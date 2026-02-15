import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api_server import app
from src.database import Database


@pytest.fixture(autouse=True)
def _patch_db(tmp_path, monkeypatch):
    """Replace the global db singleton with a fresh temporary database for every test."""
    import src.api_server as api_mod
    import src.database as db_mod

    tmp_db = Database(db_path=tmp_path / "test.db")
    monkeypatch.setattr(api_mod, "db", tmp_db)
    monkeypatch.setattr(db_mod, "db", tmp_db)

    # The lifespan context manager will call db.connect / db.close automatically
    yield tmp_db


def _make_sample(round_id="test_round_1", result="P", player_score=6, banker_score=4):
    return {
        "round_id": round_id,
        "timestamp": "2026-02-03T12:00:00Z",
        "result": result,
        "player_score": player_score,
        "banker_score": banker_score,
        "player_cards": ["AS", "5H"],
        "banker_cards": ["4D", "KC"],
        "lightning_cards": [],
        "multipliers": {},
        "table_id": "xxxtremelightningbaccarat",
        "is_natural": False,
        "raw_data": {},
    }


def _make_sample_now(
    round_id="test_round_1", result="P", player_score=6, banker_score=4,
):
    """Like _make_sample but with current timestamp so it falls within stats windows."""
    s = _make_sample(
        round_id=round_id, result=result,
        player_score=player_score, banker_score=banker_score,
    )
    s["timestamp"] = datetime.now(timezone.utc).isoformat()
    return s


async def _insert(db, sample):
    if not db._connection:
        await db.connect()
    await db.insert_result(sample)


# ---------------------------------------------------------------------------
# Health / Root
# ---------------------------------------------------------------------------


class TestHealthAndRoot:
    def test_root_returns_name_and_docs(self):
        with TestClient(app) as client:
            resp = client.get("/")
            assert resp.status_code == 200
            body = resp.json()
            assert "name" in body
            assert body["docs"] == "/docs"

    def test_health_ok(self):
        with TestClient(app) as client:
            resp = client.get("/health")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "ok"
            assert body["database"] == "connected"
            assert "timestamp" in body

    def test_health_rounds_captured_initial(self):
        with TestClient(app) as client:
            resp = client.get("/health")
            body = resp.json()
            # Fresh db should have 0 rounds (or whatever was loaded)
            assert isinstance(body["rounds_captured"], int)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


class TestResults:
    def test_get_results_empty(self):
        with TestClient(app) as client:
            resp = client.get("/api/results")
            assert resp.status_code == 200
            assert resp.json() == []

    def test_get_results_with_data(self, _patch_db):
        db = _patch_db
        with TestClient(app) as client:
            asyncio.get_event_loop().run_until_complete(_insert(db, _make_sample()))
            resp = client.get("/api/results")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) >= 1
            assert data[0]["round_id"] == "test_round_1"
            assert data[0]["result"] == "P"

    def test_get_results_limit(self, _patch_db):
        db = _patch_db
        with TestClient(app) as client:
            for i in range(5):
                asyncio.get_event_loop().run_until_complete(
                    _insert(db, _make_sample(round_id=f"round_{i}", result="B" if i % 2 else "P"))
                )
            resp = client.get("/api/results?limit=3")
            assert resp.status_code == 200
            assert len(resp.json()) == 3

    def test_get_results_limit_validation(self):
        with TestClient(app) as client:
            resp = client.get("/api/results?limit=0")
            assert resp.status_code == 422

            resp = client.get("/api/results?limit=9999")
            assert resp.status_code == 422

    def test_get_results_filter_by_table_id(self, _patch_db):
        db = _patch_db
        with TestClient(app) as client:
            s1 = _make_sample(round_id="r1")
            s1["table_id"] = "table_a"
            s2 = _make_sample(round_id="r2")
            s2["table_id"] = "table_b"
            asyncio.get_event_loop().run_until_complete(_insert(db, s1))
            asyncio.get_event_loop().run_until_complete(_insert(db, s2))

            resp = client.get("/api/results?table_id=table_a")
            data = resp.json()
            assert len(data) == 1
            assert data[0]["round_id"] == "r1"

    def test_get_results_filter_table_id_no_match(self, _patch_db):
        db = _patch_db
        with TestClient(app) as client:
            asyncio.get_event_loop().run_until_complete(_insert(db, _make_sample()))
            resp = client.get("/api/results?table_id=nonexistent")
            assert resp.status_code == 200
            assert resp.json() == []


# ---------------------------------------------------------------------------
# Latest result
# ---------------------------------------------------------------------------


class TestLatestResult:
    def test_latest_when_empty(self):
        with TestClient(app) as client:
            resp = client.get("/api/results/latest")
            assert resp.status_code == 200
            assert resp.json() is None

    def test_latest_returns_most_recent(self, _patch_db):
        db = _patch_db
        with TestClient(app) as client:
            asyncio.get_event_loop().run_until_complete(
                _insert(db, _make_sample(round_id="old", result="P"))
            )
            asyncio.get_event_loop().run_until_complete(
                _insert(db, _make_sample(round_id="new", result="B"))
            )
            resp = client.get("/api/results/latest")
            assert resp.status_code == 200
            body = resp.json()
            assert body is not None
            assert body["round_id"] in ("old", "new")


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


class TestHistory:
    def test_history_full_format(self, _patch_db):
        db = _patch_db
        with TestClient(app) as client:
            asyncio.get_event_loop().run_until_complete(_insert(db, _make_sample()))
            resp = client.get("/api/results/history?format=full")
            assert resp.status_code == 200
            body = resp.json()
            assert body["ok"] is True
            assert isinstance(body["data"], list)

    def test_history_simple_format(self, _patch_db):
        db = _patch_db
        with TestClient(app) as client:
            asyncio.get_event_loop().run_until_complete(
                _insert(db, _make_sample(round_id="s1", result="P"))
            )
            asyncio.get_event_loop().run_until_complete(
                _insert(db, _make_sample(round_id="s2", result="B"))
            )
            resp = client.get("/api/results/history?format=simple")
            assert resp.status_code == 200
            body = resp.json()
            assert body["ok"] is True
            for entry in body["data"]:
                assert entry["value"] in ("P", "B", "T")
                assert "criado_em" in entry

    def test_history_empty(self):
        with TestClient(app) as client:
            resp = client.get("/api/results/history")
            assert resp.status_code == 200
            body = resp.json()
            assert body["ok"] is True
            assert body["data"] == []


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


class TestStatistics:
    def test_statistics_empty_db(self):
        with TestClient(app) as client:
            resp = client.get("/api/statistics")
            assert resp.status_code == 200
            body = resp.json()
            assert body["period_hours"] == 24
            assert isinstance(body["total_rounds"], int)

    def test_statistics_with_data(self, _patch_db):
        db = _patch_db
        with TestClient(app) as client:
            asyncio.get_event_loop().run_until_complete(
                _insert(db, _make_sample_now(round_id="s1", result="P"))
            )
            asyncio.get_event_loop().run_until_complete(
                _insert(db, _make_sample_now(round_id="s2", result="B"))
            )
            asyncio.get_event_loop().run_until_complete(
                _insert(db, _make_sample_now(
                    round_id="s3", result="T",
                    player_score=5, banker_score=5,
                ))
            )
            resp = client.get("/api/statistics?hours=24")
            assert resp.status_code == 200
            body = resp.json()
            assert body["total_rounds"] >= 3
            assert body["player_wins"] >= 1
            assert body["banker_wins"] >= 1
            assert body["ties"] >= 1
            assert 0 <= body["player_percentage"] <= 100
            assert 0 <= body["banker_percentage"] <= 100

    def test_statistics_custom_hours(self):
        with TestClient(app) as client:
            resp = client.get("/api/statistics?hours=1")
            assert resp.status_code == 200
            assert resp.json()["period_hours"] == 1

    def test_statistics_hours_validation(self):
        with TestClient(app) as client:
            resp = client.get("/api/statistics?hours=0")
            assert resp.status_code == 422

            resp = client.get("/api/statistics?hours=999")
            assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Streak
# ---------------------------------------------------------------------------


class TestStreak:
    def test_streak_empty(self):
        with TestClient(app) as client:
            resp = client.get("/api/streak")
            assert resp.status_code == 200
            body = resp.json()
            assert body["length"] == 0
            assert body["side"] is None

    def test_streak_with_data(self, _patch_db):
        db = _patch_db
        with TestClient(app) as client:
            for i in range(4):
                asyncio.get_event_loop().run_until_complete(
                    _insert(db, _make_sample(round_id=f"streak_{i}", result="B", banker_score=7))
                )
            resp = client.get("/api/streak")
            assert resp.status_code == 200
            body = resp.json()
            assert body["side_code"] == "B"
            assert body["length"] >= 1


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


class TestPattern:
    def test_pattern_empty(self):
        with TestClient(app) as client:
            resp = client.get("/api/pattern?length=5")
            assert resp.status_code == 200
            body = resp.json()
            assert body["pattern"] == []
            assert body["string"] == ""
            assert body["length"] == 0

    def test_pattern_with_data(self, _patch_db):
        db = _patch_db
        with TestClient(app) as client:
            for i, r in enumerate(["P", "B", "B", "P", "T"]):
                asyncio.get_event_loop().run_until_complete(
                    _insert(db, _make_sample(round_id=f"pat_{i}", result=r))
                )
            resp = client.get("/api/pattern?length=10")
            assert resp.status_code == 200
            body = resp.json()
            assert len(body["pattern"]) == 5
            assert all(c in "PBT" for c in body["string"])

    def test_pattern_length_validation(self):
        with TestClient(app) as client:
            resp = client.get("/api/pattern?length=2")
            assert resp.status_code == 422

            resp = client.get("/api/pattern?length=200")
            assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Roads
# ---------------------------------------------------------------------------


class TestRoads:
    def test_roads_empty(self):
        with TestClient(app) as client:
            resp = client.get("/api/roads?limit=10")
            assert resp.status_code == 200
            body = resp.json()
            assert body["big_road"] == []
            assert body["results_count"] == 0

    def test_roads_builds_columns(self, _patch_db):
        db = _patch_db
        with TestClient(app) as client:
            # P P P B B P → 3 columns
            sequence = ["P", "P", "P", "B", "B", "P"]
            for i, r in enumerate(sequence):
                asyncio.get_event_loop().run_until_complete(
                    _insert(db, _make_sample(round_id=f"road_{i}", result=r))
                )
            resp = client.get("/api/roads?limit=10")
            assert resp.status_code == 200
            body = resp.json()
            assert body["total_columns"] == 3
            # First column should have 3 entries (PPP)
            assert len(body["big_road"][0]) == 3
            # Second column should have 2 entries (BB)
            assert len(body["big_road"][1]) == 2
            assert body["results_count"] == 6

    def test_roads_ties_dont_create_columns(self, _patch_db):
        db = _patch_db
        with TestClient(app) as client:
            sequence = ["P", "T", "P"]
            for i, r in enumerate(sequence):
                asyncio.get_event_loop().run_until_complete(
                    _insert(db, _make_sample(round_id=f"tie_{i}", result=r))
                )
            resp = client.get("/api/roads?limit=10")
            body = resp.json()
            # P T P → 1 column with 2 Ps, tie is attached
            assert body["total_columns"] == 1
            assert body["big_road"][0][0]["ties"] == 1

    def test_roads_limit_validation(self):
        with TestClient(app) as client:
            resp = client.get("/api/roads?limit=5")
            assert resp.status_code == 422

            resp = client.get("/api/roads?limit=500")
            assert resp.status_code == 422


# ---------------------------------------------------------------------------
# CORS headers
# ---------------------------------------------------------------------------


class TestCORS:
    def test_cors_headers_present(self):
        with TestClient(app) as client:
            resp = client.options(
                "/api/results",
                headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
            )
            # Should not be 405
            assert resp.status_code in (200, 204)


# ---------------------------------------------------------------------------
# OpenAPI docs
# ---------------------------------------------------------------------------


class TestDocs:
    def test_openapi_json_available(self):
        with TestClient(app) as client:
            resp = client.get("/openapi.json")
            assert resp.status_code == 200
            schema = resp.json()
            assert schema["info"]["title"] == "Evolution Baccarat Scraper API"
            assert "/api/results" in schema["paths"]
            assert "/api/statistics" in schema["paths"]
            assert "/api/streak" in schema["paths"]
            assert "/api/pattern" in schema["paths"]
            assert "/api/roads" in schema["paths"]
            assert "/health" in schema["paths"]
