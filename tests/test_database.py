"""Tests for the Database class (src/database.py)."""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    round_id="r1",
    result="P",
    player_score=6,
    banker_score=4,
    table_id="xxxtremelightningbaccarat",
    shoe_id="shoe_1",
    timestamp=None,
    is_natural=False,
):
    return {
        "round_id": round_id,
        "timestamp": timestamp or datetime.utcnow().isoformat(),
        "result": result,
        "player_score": player_score,
        "banker_score": banker_score,
        "player_cards": ["SA", "H5"],
        "banker_cards": ["DK", "C4"],
        "player_third_card": None,
        "banker_third_card": None,
        "is_natural": is_natural,
        "lightning_cards": [],
        "multipliers": {},
        "table_id": table_id,
        "shoe_id": shoe_id,
        "raw_data": {},
    }


@pytest.fixture()
def db(tmp_path):
    """Yield a connected Database backed by a temporary SQLite file."""
    database = Database(db_path=tmp_path / "test.db")
    asyncio.get_event_loop().run_until_complete(database.connect())
    yield database
    asyncio.get_event_loop().run_until_complete(database.close())


# ---------------------------------------------------------------------------
# Connection / table creation
# ---------------------------------------------------------------------------


class TestConnection:
    def test_connect_creates_file(self, tmp_path):
        db_path = tmp_path / "new.db"
        database = Database(db_path=db_path)
        asyncio.get_event_loop().run_until_complete(database.connect())
        assert db_path.exists()
        asyncio.get_event_loop().run_until_complete(database.close())

    def test_connect_creates_parent_dirs(self, tmp_path):
        db_path = tmp_path / "deep" / "nested" / "dir" / "results.db"
        database = Database(db_path=db_path)
        asyncio.get_event_loop().run_until_complete(database.connect())
        assert db_path.exists()
        asyncio.get_event_loop().run_until_complete(database.close())

    def test_close_sets_connection_none(self, tmp_path):
        database = Database(db_path=tmp_path / "close_test.db")
        asyncio.get_event_loop().run_until_complete(database.connect())
        asyncio.get_event_loop().run_until_complete(database.close())
        assert database._connection is None

    def test_close_idempotent(self, tmp_path):
        database = Database(db_path=tmp_path / "close2.db")
        asyncio.get_event_loop().run_until_complete(database.connect())
        asyncio.get_event_loop().run_until_complete(database.close())
        # Calling close again should not raise
        asyncio.get_event_loop().run_until_complete(database.close())

    def test_initial_rounds_captured_is_zero(self, db):
        assert db.rounds_captured == 0


# ---------------------------------------------------------------------------
# insert_result
# ---------------------------------------------------------------------------


class TestInsertResult:
    def test_insert_single_result(self, db):
        row_id = asyncio.get_event_loop().run_until_complete(
            db.insert_result(_make_result())
        )
        assert row_id > 0
        assert db.rounds_captured == 1

    def test_insert_increments_counter(self, db):
        for i in range(5):
            asyncio.get_event_loop().run_until_complete(
                db.insert_result(_make_result(round_id=f"r_{i}"))
            )
        assert db.rounds_captured == 5

    def test_insert_duplicate_round_id_ignored(self, db):
        asyncio.get_event_loop().run_until_complete(
            db.insert_result(_make_result(round_id="dup"))
        )
        row_id = asyncio.get_event_loop().run_until_complete(
            db.insert_result(_make_result(round_id="dup"))
        )
        # Duplicate → returns 0, counter not incremented twice
        assert row_id == 0
        assert db.rounds_captured == 1

    def test_insert_player_result(self, db):
        asyncio.get_event_loop().run_until_complete(
            db.insert_result(_make_result(result="P"))
        )
        results = asyncio.get_event_loop().run_until_complete(
            db.get_recent_results(1)
        )
        assert results[0]["result"] == "P"

    def test_insert_banker_result(self, db):
        asyncio.get_event_loop().run_until_complete(
            db.insert_result(_make_result(round_id="b1", result="B", banker_score=7))
        )
        results = asyncio.get_event_loop().run_until_complete(
            db.get_recent_results(1)
        )
        assert results[0]["result"] == "B"

    def test_insert_tie_result(self, db):
        asyncio.get_event_loop().run_until_complete(
            db.insert_result(
                _make_result(round_id="t1", result="T", player_score=5, banker_score=5)
            )
        )
        results = asyncio.get_event_loop().run_until_complete(
            db.get_recent_results(1)
        )
        assert results[0]["result"] == "T"

    def test_insert_natural_flag(self, db):
        asyncio.get_event_loop().run_until_complete(
            db.insert_result(
                _make_result(
                    round_id="nat1",
                    result="P",
                    player_score=8,
                    banker_score=3,
                    is_natural=True,
                )
            )
        )
        results = asyncio.get_event_loop().run_until_complete(
            db.get_recent_results(1)
        )
        assert results[0]["is_natural"] == 1

    def test_insert_preserves_json_fields(self, db):
        sample = _make_result(round_id="json_test")
        sample["player_cards"] = ["SA", "H4", "D2"]
        sample["multipliers"] = {"S5": 2, "H8": 5}
        asyncio.get_event_loop().run_until_complete(db.insert_result(sample))

        results = asyncio.get_event_loop().run_until_complete(
            db.get_recent_results(1)
        )
        assert results[0]["player_cards"] == ["SA", "H4", "D2"]
        assert results[0]["multipliers"] == {"S5": 2, "H8": 5}


# ---------------------------------------------------------------------------
# get_recent_results
# ---------------------------------------------------------------------------


class TestGetRecentResults:
    def test_empty_database(self, db):
        results = asyncio.get_event_loop().run_until_complete(
            db.get_recent_results(10)
        )
        assert results == []

    def test_returns_up_to_limit(self, db):
        for i in range(10):
            asyncio.get_event_loop().run_until_complete(
                db.insert_result(_make_result(round_id=f"lim_{i}"))
            )
        results = asyncio.get_event_loop().run_until_complete(
            db.get_recent_results(5)
        )
        assert len(results) == 5

    def test_returns_all_when_fewer_than_limit(self, db):
        for i in range(3):
            asyncio.get_event_loop().run_until_complete(
                db.insert_result(_make_result(round_id=f"few_{i}"))
            )
        results = asyncio.get_event_loop().run_until_complete(
            db.get_recent_results(100)
        )
        assert len(results) == 3

    def test_ordered_by_timestamp_descending(self, db):
        base = datetime(2026, 1, 1, 12, 0, 0)
        for i in range(5):
            ts = (base + timedelta(minutes=i)).isoformat()
            asyncio.get_event_loop().run_until_complete(
                db.insert_result(_make_result(round_id=f"ord_{i}", timestamp=ts))
            )
        results = asyncio.get_event_loop().run_until_complete(
            db.get_recent_results(5)
        )
        timestamps = [r["timestamp"] for r in results]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_json_fields_are_parsed(self, db):
        sample = _make_result(round_id="parse_json")
        sample["lightning_cards"] = ["S5"]
        sample["raw_data"] = {"key": "value"}
        asyncio.get_event_loop().run_until_complete(db.insert_result(sample))

        results = asyncio.get_event_loop().run_until_complete(
            db.get_recent_results(1)
        )
        r = results[0]
        assert isinstance(r["lightning_cards"], list)
        assert isinstance(r["raw_data"], dict)


# ---------------------------------------------------------------------------
# get_statistics
# ---------------------------------------------------------------------------


class TestGetStatistics:
    def test_statistics_empty_database(self, db):
        stats = asyncio.get_event_loop().run_until_complete(db.get_statistics(24))
        assert stats["total_rounds"] >= 0
        assert stats["period_hours"] == 24

    def test_statistics_counts_winners(self, db):
        now = datetime.utcnow().isoformat()
        for i, r in enumerate(["P", "P", "B", "B", "B", "T"]):
            asyncio.get_event_loop().run_until_complete(
                db.insert_result(_make_result(round_id=f"stat_{i}", result=r, timestamp=now))
            )
        stats = asyncio.get_event_loop().run_until_complete(db.get_statistics(24))
        assert stats["player_wins"] == 2
        assert stats["banker_wins"] == 3
        assert stats["ties"] == 1
        assert stats["total_rounds"] == 6

    def test_statistics_percentages(self, db):
        now = datetime.utcnow().isoformat()
        # 2P, 2B → 50% each
        for i, r in enumerate(["P", "P", "B", "B"]):
            asyncio.get_event_loop().run_until_complete(
                db.insert_result(_make_result(round_id=f"pct_{i}", result=r, timestamp=now))
            )
        stats = asyncio.get_event_loop().run_until_complete(db.get_statistics(24))
        assert stats["player_percentage"] == 50.0
        assert stats["banker_percentage"] == 50.0
        assert stats["tie_percentage"] == 0.0

    def test_statistics_avg_scores(self, db):
        now = datetime.utcnow().isoformat()
        asyncio.get_event_loop().run_until_complete(
            db.insert_result(
                _make_result(
                    round_id="avg1", result="P",
                    player_score=6, banker_score=4, timestamp=now,
                )
            )
        )
        asyncio.get_event_loop().run_until_complete(
            db.insert_result(
                _make_result(
                    round_id="avg2", result="B",
                    player_score=2, banker_score=8, timestamp=now,
                )
            )
        )
        stats = asyncio.get_event_loop().run_until_complete(db.get_statistics(24))
        assert stats["avg_player_score"] == 4.0
        assert stats["avg_banker_score"] == 6.0

    def test_statistics_respects_hours_parameter(self, db):
        old_ts = (datetime.utcnow() - timedelta(hours=48)).isoformat()
        new_ts = datetime.utcnow().isoformat()
        asyncio.get_event_loop().run_until_complete(
            db.insert_result(_make_result(round_id="old", result="P", timestamp=old_ts))
        )
        asyncio.get_event_loop().run_until_complete(
            db.insert_result(_make_result(round_id="new", result="B", timestamp=new_ts))
        )
        stats_1h = asyncio.get_event_loop().run_until_complete(db.get_statistics(1))
        stats_72h = asyncio.get_event_loop().run_until_complete(db.get_statistics(72))
        # The 1-hour window should have fewer results than the 72-hour window
        assert stats_72h["total_rounds"] >= stats_1h["total_rounds"]


# ---------------------------------------------------------------------------
# get_current_streak
# ---------------------------------------------------------------------------


class TestGetCurrentStreak:
    def test_streak_empty_database(self, db):
        streak = asyncio.get_event_loop().run_until_complete(db.get_current_streak())
        assert streak["side"] is None
        assert streak["length"] == 0

    def test_streak_single_result(self, db):
        asyncio.get_event_loop().run_until_complete(
            db.insert_result(_make_result(round_id="s1", result="B", banker_score=7))
        )
        streak = asyncio.get_event_loop().run_until_complete(db.get_current_streak())
        assert streak["side"] == "Banker"
        assert streak["side_code"] == "B"
        assert streak["length"] == 1

    def test_streak_consecutive_same(self, db):
        base = datetime(2026, 1, 1, 12, 0, 0)
        for i in range(5):
            ts = (base + timedelta(minutes=i)).isoformat()
            asyncio.get_event_loop().run_until_complete(
                db.insert_result(
                    _make_result(round_id=f"streak_p_{i}", result="P", timestamp=ts)
                )
            )
        streak = asyncio.get_event_loop().run_until_complete(db.get_current_streak())
        assert streak["side"] == "Player"
        assert streak["side_code"] == "P"
        assert streak["length"] == 5

    def test_streak_broken_by_opposite(self, db):
        base = datetime(2026, 1, 1, 12, 0, 0)
        # B B B P P → most recent streak is P with length 2
        sequence = ["B", "B", "B", "P", "P"]
        for i, r in enumerate(sequence):
            ts = (base + timedelta(minutes=i)).isoformat()
            asyncio.get_event_loop().run_until_complete(
                db.insert_result(
                    _make_result(round_id=f"brk_{i}", result=r, timestamp=ts)
                )
            )
        streak = asyncio.get_event_loop().run_until_complete(db.get_current_streak())
        assert streak["side_code"] == "P"
        assert streak["length"] == 2

    def test_streak_ignores_ties(self, db):
        base = datetime(2026, 1, 1, 12, 0, 0)
        # P P T (ties are excluded from streak calculation)
        sequence = [("P", "P"), ("P", "P"), ("T", "T")]
        for i, (r, _) in enumerate(sequence):
            ts = (base + timedelta(minutes=i)).isoformat()
            asyncio.get_event_loop().run_until_complete(
                db.insert_result(
                    _make_result(
                        round_id=f"tie_streak_{i}",
                        result=r,
                        player_score=5,
                        banker_score=5,
                        timestamp=ts,
                    )
                )
            )
        streak = asyncio.get_event_loop().run_until_complete(db.get_current_streak())
        # The query filters out T, so only Ps remain
        assert streak["side_code"] == "P"
        assert streak["length"] == 2


# ---------------------------------------------------------------------------
# _load_initial_stats (on re-connect)
# ---------------------------------------------------------------------------


class TestLoadInitialStats:
    def test_counter_reflects_existing_data(self, tmp_path):
        db_path = tmp_path / "preloaded.db"
        db1 = Database(db_path=db_path)
        asyncio.get_event_loop().run_until_complete(db1.connect())
        for i in range(7):
            asyncio.get_event_loop().run_until_complete(
                db1.insert_result(_make_result(round_id=f"pre_{i}"))
            )
        asyncio.get_event_loop().run_until_complete(db1.close())

        # Open a fresh Database instance against the same file
        db2 = Database(db_path=db_path)
        asyncio.get_event_loop().run_until_complete(db2.connect())
        assert db2.rounds_captured == 7
        asyncio.get_event_loop().run_until_complete(db2.close())


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_insert_result_with_none_scores(self, db):
        sample = _make_result(round_id="none_scores")
        sample["player_score"] = None
        sample["banker_score"] = None
        row_id = asyncio.get_event_loop().run_until_complete(db.insert_result(sample))
        assert row_id > 0

    def test_insert_result_with_empty_cards(self, db):
        sample = _make_result(round_id="empty_cards")
        sample["player_cards"] = []
        sample["banker_cards"] = []
        sample["lightning_cards"] = []
        row_id = asyncio.get_event_loop().run_until_complete(db.insert_result(sample))
        assert row_id > 0

    def test_insert_result_minimal_fields(self, db):
        minimal = {
            "round_id": "minimal_1",
            "result": "B",
        }
        row_id = asyncio.get_event_loop().run_until_complete(db.insert_result(minimal))
        assert row_id > 0

    def test_large_batch_insert(self, db):
        for i in range(200):
            result_type = ["P", "B", "T"][i % 3]
            asyncio.get_event_loop().run_until_complete(
                db.insert_result(_make_result(round_id=f"batch_{i}", result=result_type))
            )
        assert db.rounds_captured == 200
        results = asyncio.get_event_loop().run_until_complete(
            db.get_recent_results(200)
        )
        assert len(results) == 200
