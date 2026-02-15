"""
Lightning Baccarat Multiplier Tracker
Tracks and analyzes Lightning multipliers from Evolution Gaming
"""
import logging
from collections import deque
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class LightningTracker:
    """Tracks Lightning multipliers and calculates statistics"""
    
    def __init__(self, history_size: int = 50):
        """
        Initialize Lightning Tracker
        
        Args:
            history_size: Number of rounds to keep in history
        """
        self.history_size = history_size
        self.multiplier_history = deque(maxlen=history_size)
        self.total_rounds = 0
        
    def record_round(self, game_id: str, multipliers_dict: Dict) -> None:
        """
        Record multipliers from a round
        
        Args:
            game_id: Game identifier
            multipliers_dict: Dictionary with multipliers (e.g., {"2": ["P5"], "3": ["B7"], "5": ["P8"]})
        """
        if not multipliers_dict:
            return
            
        # Extract all multipliers into a flat list
        multipliers = []
        for mult_str, positions in multipliers_dict.items():
            try:
                mult_value = int(mult_str)
                count = len(positions) if isinstance(positions, list) else 1
                multipliers.extend([mult_value] * count)
            except (ValueError, TypeError):
                logger.warning(f"Invalid multiplier value: {mult_str}")
                continue
        
        if multipliers:
            self.multiplier_history.append(multipliers)
            self.total_rounds += 1
            logger.debug(f"Recorded {len(multipliers)} multipliers for game {game_id}")
    
    def get_stats(self) -> Dict:
        """
        Get statistics about multipliers
        
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
        
        # Flatten all multipliers
        all_multipliers = []
        for round_mults in self.multiplier_history:
            all_multipliers.extend(round_mults)
        
        if not all_multipliers:
            return {
                'avg_multiplier': 1.0,
                'distribution': {},
                'hot_streak': False,
                'total_rounds': len(self.multiplier_history)
            }
        
        # Calculate average
        avg_multiplier = sum(all_multipliers) / len(all_multipliers)
        
        # Calculate distribution
        distribution = {}
        total_count = len(all_multipliers)
        for mult in [2, 3, 5, 8]:
            count = all_multipliers.count(mult)
            distribution[mult] = count / total_count if total_count > 0 else 0
        
        # Check for hot streak (high frequency of 5x+ in recent rounds)
        hot_streak = self.is_hot_table()
        
        return {
            'avg_multiplier': round(avg_multiplier, 2),
            'distribution': distribution,
            'hot_streak': hot_streak,
            'total_rounds': len(self.multiplier_history)
        }
    
    def get_ev_multiplier(self) -> float:
        """
        Get the average multiplier for EV calculations
        
        Returns:
            Weighted average multiplier
        """
        if not self.multiplier_history:
            return 1.0
        
        # Flatten all multipliers
        all_multipliers = []
        for round_mults in self.multiplier_history:
            all_multipliers.extend(round_mults)
        
        if not all_multipliers:
            return 1.0
        
        # Return average multiplier
        return sum(all_multipliers) / len(all_multipliers)
    
    def is_hot_table(self) -> bool:
        """
        Check if table has high frequency of high multipliers (>=5x)
        
        A table is considered "hot" when more than 25% of multipliers are 5x or higher.
        This threshold (0.25) is based on the fact that in normal Lightning distribution,
        high multipliers (5x, 8x) are relatively rare. A frequency above 25% indicates
        an unusual concentration of high multipliers, suggesting favorable betting conditions.
        
        Returns:
            True if hot table detected
        """
        if len(self.multiplier_history) < 10:
            return False
        
        # Count high multipliers (5x or 8x) in recent history
        high_mult_count = 0
        total_mult_count = 0
        
        for round_mults in self.multiplier_history:
            for mult in round_mults:
                total_mult_count += 1
                if mult >= 5:
                    high_mult_count += 1
        
        if total_mult_count == 0:
            return False
        
        # Hot table if >25% of multipliers are 5x or higher
        HOT_TABLE_THRESHOLD = 0.25
        high_mult_ratio = high_mult_count / total_mult_count
        return high_mult_ratio > HOT_TABLE_THRESHOLD
    
    def format_distribution(self) -> str:
        """
        Format distribution as readable string
        
        Returns:
            Formatted string like "2x(45%) 3x(30%) 5x(15%) 8x(10%)"
        """
        stats = self.get_stats()
        distribution = stats['distribution']
        
        if not distribution:
            return "Sin datos"
        
        parts = []
        for mult in [2, 3, 5, 8]:
            pct = distribution.get(mult, 0) * 100
            parts.append(f"{mult}x({pct:.0f}%)")
        
        return " ".join(parts)
