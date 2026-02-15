import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper import EvolutionScraper

# ---------------------------------------------------------------------------
# _extract_baccarat_result
# ---------------------------------------------------------------------------


def test_extract_baccarat_result_player_natural():
    scraper = EvolutionScraper()
    data = {
        "data": {
            "winner": "PLAYER",
            "roundId": 123,
            "playerScore": 8,
            "bankerScore": 1,
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["result"] == "P"
    assert result["player_score"] == 8
    assert result["banker_score"] == 1
    assert result["is_natural"] is True


def test_extract_baccarat_result_banker_natural_with_zero():
    scraper = EvolutionScraper()
    data = {
        "result": {
            "winner": "BANKER",
            "roundId": "r1",
            "playerScore": 0,
            "bankerScore": 9,
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["result"] == "B"
    assert result["player_score"] == 0
    assert result["banker_score"] == 9
    assert result["is_natural"] is True


def test_extract_baccarat_result_tie():
    scraper = EvolutionScraper()
    data = {
        "data": {
            "winner": "TIE",
            "roundId": "t1",
            "playerScore": 6,
            "bankerScore": 6,
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["result"] == "T"
    assert result["player_score"] == 6
    assert result["banker_score"] == 6


def test_extract_baccarat_result_invalid():
    scraper = EvolutionScraper()
    data = {"data": {"winner": "UNKNOWN", "roundId": "r2"}}
    result = scraper._extract_baccarat_result(data)
    assert result is None


def test_extract_baccarat_result_empty_dict():
    scraper = EvolutionScraper()
    result = scraper._extract_baccarat_result({})
    assert result is None


def test_extract_baccarat_result_not_a_dict():
    scraper = EvolutionScraper()
    assert scraper._extract_baccarat_result("string") is None
    assert scraper._extract_baccarat_result(42) is None
    assert scraper._extract_baccarat_result(None) is None
    assert scraper._extract_baccarat_result([]) is None


def test_extract_baccarat_result_nested_game_result():
    """Evolution sometimes nests under 'gameResult'"""
    scraper = EvolutionScraper()
    data = {
        "gameResult": {
            "winner": "PLAYER",
            "roundId": "gr1",
            "playerScore": 7,
            "bankerScore": 3,
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["result"] == "P"
    assert result["round_id"] == "gr1"


def test_extract_baccarat_result_nested_round_result():
    scraper = EvolutionScraper()
    data = {
        "roundResult": {
            "outcome": "BANKER",
            "id": "rr100",
            "playerTotal": 4,
            "bankerTotal": 5,
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["result"] == "B"
    assert result["round_id"] == "rr100"
    assert result["player_score"] == 4
    assert result["banker_score"] == 5


def test_extract_baccarat_result_flat_data():
    """Result data directly in root dict (no nesting)"""
    scraper = EvolutionScraper()
    data = {
        "winner": "PLAYER",
        "roundId": "flat1",
        "playerScore": 6,
        "bankerScore": 2,
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["result"] == "P"
    assert result["round_id"] == "flat1"


def test_extract_baccarat_result_short_codes():
    """Some Evolution messages use single-letter codes"""
    scraper = EvolutionScraper()
    data = {
        "data": {
            "winner": "P",
            "roundId": "sc1",
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["result"] == "P"


def test_extract_baccarat_result_winning_hand_key():
    scraper = EvolutionScraper()
    data = {
        "data": {
            "winningHand": "BANKER",
            "roundId": "wh1",
            "playerScore": 3,
            "bankerScore": 7,
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["result"] == "B"


def test_extract_baccarat_result_missing_scores():
    """Result with no scores should still extract the winner"""
    scraper = EvolutionScraper()
    data = {
        "data": {
            "winner": "PLAYER",
            "roundId": "ns1",
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["result"] == "P"
    assert result["player_score"] is None
    assert result["banker_score"] is None
    # No scores → is_natural should be False
    assert result["is_natural"] is False


def test_extract_baccarat_result_auto_round_id():
    """When no roundId is present, a synthetic one is generated"""
    scraper = EvolutionScraper()
    data = {
        "data": {
            "winner": "BANKER",
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["round_id"].startswith("evo_")


def test_extract_baccarat_result_cards():
    scraper = EvolutionScraper()
    data = {
        "data": {
            "winner": "PLAYER",
            "roundId": "cards1",
            "playerScore": 5,
            "bankerScore": 3,
            "playerCards": ["SA", "H4"],
            "bankerCards": ["DK", "C3"],
            "lightningCards": ["S5", "H8"],
            "multipliers": {"S5": 2, "H8": 5},
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["player_cards"] == ["SA", "H4"]
    assert result["banker_cards"] == ["DK", "C3"]
    assert result["lightning_cards"] == ["S5", "H8"]
    assert result["multipliers"] == {"S5": 2, "H8": 5}


def test_extract_baccarat_result_non_natural():
    """Scores below 8 are not naturals"""
    scraper = EvolutionScraper()
    data = {
        "data": {
            "winner": "BANKER",
            "roundId": "nn1",
            "playerScore": 5,
            "bankerScore": 7,
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["is_natural"] is False


def test_extract_baccarat_result_natural_eight():
    scraper = EvolutionScraper()
    data = {
        "data": {
            "winner": "PLAYER",
            "roundId": "n8",
            "playerScore": 8,
            "bankerScore": 3,
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["is_natural"] is True


def test_extract_baccarat_result_invalid_score_type():
    """Scores that can't be parsed to int should become None"""
    scraper = EvolutionScraper()
    data = {
        "data": {
            "winner": "PLAYER",
            "roundId": "inv_score",
            "playerScore": "N/A",
            "bankerScore": "error",
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["result"] == "P"
    assert result["player_score"] is None
    assert result["banker_score"] is None


def test_extract_uses_alternative_score_keys():
    """playerPoints / bankerPoints keys"""
    scraper = EvolutionScraper()
    data = {
        "data": {
            "winner": "BANKER",
            "roundId": "alt_keys",
            "playerPoints": 2,
            "bankerPoints": 6,
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert result["player_score"] == 2
    assert result["banker_score"] == 6


# ---------------------------------------------------------------------------
# _validate_result
# ---------------------------------------------------------------------------


def test_validate_result_valid():
    scraper = EvolutionScraper()
    assert scraper._validate_result({"round_id": "r1", "result": "P"}) is True
    assert scraper._validate_result({"round_id": "r2", "result": "B"}) is True
    assert scraper._validate_result({"round_id": "r3", "result": "T"}) is True


def test_validate_result_missing_round_id():
    scraper = EvolutionScraper()
    assert scraper._validate_result({"result": "P"}) is False
    assert scraper._validate_result({"round_id": "", "result": "P"}) is False
    assert scraper._validate_result({"round_id": None, "result": "P"}) is False


def test_validate_result_missing_result():
    scraper = EvolutionScraper()
    assert scraper._validate_result({"round_id": "r1"}) is False
    assert scraper._validate_result({"round_id": "r1", "result": ""}) is False
    assert scraper._validate_result({"round_id": "r1", "result": None}) is False


def test_validate_result_invalid_result_value():
    scraper = EvolutionScraper()
    assert scraper._validate_result({"round_id": "r1", "result": "X"}) is False
    assert scraper._validate_result({"round_id": "r1", "result": "PLAYER"}) is False
    assert scraper._validate_result({"round_id": "r1", "result": "banker"}) is False


def test_validate_result_empty_dict():
    scraper = EvolutionScraper()
    assert scraper._validate_result({}) is False


# ---------------------------------------------------------------------------
# _is_stale / _should_refresh_session
# ---------------------------------------------------------------------------


def test_is_stale_no_frame():
    """When no frames have been received, not stale (nothing to compare)"""
    scraper = EvolutionScraper()
    assert scraper._is_stale() is False


def test_should_refresh_session_initially():
    """Without a last refresh timestamp, refresh is needed"""
    scraper = EvolutionScraper()
    scraper.last_session_refresh_at = None
    assert scraper._should_refresh_session() is True


# ---------------------------------------------------------------------------
# Integration-style: extract → validate round-trip
# ---------------------------------------------------------------------------


def test_extract_then_validate_roundtrip():
    scraper = EvolutionScraper()
    data = {
        "data": {
            "winner": "BANKER",
            "roundId": "rt1",
            "playerScore": 4,
            "bankerScore": 7,
        }
    }
    result = scraper._extract_baccarat_result(data)
    assert result is not None
    assert scraper._validate_result(result) is True


def test_extract_invalid_winner_then_validate():
    scraper = EvolutionScraper()
    data = {"data": {"winner": "DRAW", "roundId": "bad"}}
    result = scraper._extract_baccarat_result(data)
    # _extract should return None for invalid winners
    assert result is None
