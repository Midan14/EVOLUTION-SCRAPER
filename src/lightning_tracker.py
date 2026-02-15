"""
Lightning Baccarat Multiplier Tracker
Tracks Lightning multipliers (2x, 3x, 5x, 8x) and provides statistics
"""
import logging
import os
from collections import deque
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Default history size - can be overridden by config
DEFAULT_HISTORY_SIZE = 50


class LightningTracker:
    """Tracks Lightning Baccarat multipliers and provides EV calculations"""

    def __init__(self, history_size: Optional[int] = None):
        """
        Initialize Lightning Tracker

        Args:
            history_size: Number of rounds to track (default from config or 50)
        """
        if history_size is None:
            history_size = int(os.getenv("MULTIPLIER_HISTORY_SIZE", str(DEFAULT_HISTORY_SIZE)))

        self.history_size = history_size
        self.multiplier_history: deque[Dict[str, float]] = deque(maxlen=self.history_size)
        self.total_rounds = 0

        logger.info(f"✅ LightningTracker initialized with history_size={history_size}")

    def record_round(self, game_id: str, multipliers_dict: Dict[str, float]) -> None:
        """
        Record multipliers for a round

        Args:
            game_id: Game identifier
            multipliers_dict: Dictionary with 'player' and 'banker' multipliers
                Example: {'player': 2.0, 'banker': 5.0}
        """
        player_mult = multipliers_dict.get('player', 1.0)
        banker_mult = multipliers_dict.get('banker', 1.0)

        self.multiplier_history.append({
            'game_id': game_id,
            'player': player_mult,
            'banker': banker_mult,
            'max': max(player_mult, banker_mult)
        })

        self.total_rounds += 1

        logger.debug(f"📊 Round {game_id}: P={player_mult}x B={banker_mult}x")

    def get_stats(self) -> Dict:
        """
        Get comprehensive statistics

        Returns:
            Dictionary with avg_multiplier, distribution, hot_streak, total_rounds
        """
        if not self.multiplier_history:
            return {
                'avg_multiplier': 1.0,
                'distribution': {},
                'hot_streak': False,
                'total_rounds': 0
            }

        # Calculate average multiplier
        all_mults = []
        for record in self.multiplier_history:
            all_mults.extend([record['player'], record['banker']])

        avg_multiplier = sum(all_mults) / len(all_mults) if all_mults else 1.0

        # Calculate distribution
        distribution = self._calculate_distribution()

        # Determine if table is hot
        hot_streak = self.is_hot_table()

        return {
            'avg_multiplier': avg_multiplier,
            'distribution': distribution,
            'hot_streak': hot_streak,
            'total_rounds': len(self.multiplier_history)
        }

    def get_ev_multiplier(self) -> float:
        """
        Get average multiplier for EV calculations

        Returns:
            Average multiplier across all positions
        """
        if not self.multiplier_history:
            return 1.0

        all_mults = []
        for record in self.multiplier_history:
            all_mults.extend([record['player'], record['banker']])

        return sum(all_mults) / len(all_mults) if all_mults else 1.0

    def is_hot_table(self) -> bool:
        """
        Determine if table is "hot" (>25% high multipliers >=5x)

        Returns:
            True if hot table, False otherwise
        """
        if not self.multiplier_history:
            return False

        high_mult_count = 0
        total_mults = 0

        for record in self.multiplier_history:
            if record['player'] >= 5.0:
                high_mult_count += 1
            if record['banker'] >= 5.0:
                high_mult_count += 1
            total_mults += 2

        if total_mults == 0:
            return False

        hot_percentage = (high_mult_count / total_mults) * 100
        return hot_percentage > 25.0

    def format_distribution(self) -> str:
        """
        Format distribution as string: "2x(45%) 3x(30%) 5x(15%) 8x(10%)"

        Returns:
            Formatted distribution string
        """
        if not self.multiplier_history:
            return "No data"

        distribution = self._calculate_distribution()

        if not distribution:
            return "No data"

        # Sort by multiplier value
        sorted_mults = sorted(distribution.items())

        parts = []
        for mult, pct in sorted_mults:
            parts.append(f"{mult}x({pct:.0f}%)")

        return " ".join(parts)

    def _calculate_distribution(self) -> Dict[float, float]:
        """
        Calculate distribution of multipliers

        Returns:
            Dictionary mapping multiplier -> percentage
        """
        if not self.multiplier_history:
            return {}

        mult_counts: Dict[float, int] = {}
        total_count = 0

        for record in self.multiplier_history:
            for mult in [record['player'], record['banker']]:
                mult_counts[mult] = mult_counts.get(mult, 0) + 1
                total_count += 1

        # Convert counts to percentages
        distribution = {}
        for mult, count in mult_counts.items():
            distribution[mult] = (count / total_count) * 100

        return distribution

    def get_recent_multipliers(self, count: int = 10) -> List[Dict]:
        """
        Get recent multiplier records

        Args:
            count: Number of recent records to return

        Returns:
            List of recent multiplier records
        """
        recent = list(self.multiplier_history)[-count:]
        return recent

    def reset(self) -> None:
        """Reset all tracking data"""
        self.multiplier_history.clear()
        self.total_rounds = 0
        logger.info("🔄 LightningTracker reset")
