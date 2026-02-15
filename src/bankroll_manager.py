"""
Bankroll Manager for Lightning Baccarat
Manages bankroll, calculates EV, generates betting signals with Kelly criterion
"""
import logging
from typing import Dict, Optional

from src.ev_calculator import calculate_banker_ev, calculate_player_ev, format_ev

logger = logging.getLogger(__name__)


class BankrollManager:
    """Manages bankroll and betting decisions for Lightning Baccarat"""

    def __init__(
        self,
        initial_bankroll: float = 1000.0,
        lightning_fee: float = 0.50,
        banker_commission: float = 0.05,
        kelly_fraction: float = 0.25,
        min_ev: float = 0.02
    ):
        """
        Initialize Bankroll Manager

        Args:
            initial_bankroll: Starting bankroll (default 1000)
            lightning_fee: Lightning fee percentage (default 0.50 = 50%)
            banker_commission: Banker commission (default 0.05 = 5%)
            kelly_fraction: Fraction of Kelly to use (default 0.25 = 25%)
            min_ev: Minimum EV required to bet (default 0.02 = 2%)
        """
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.lightning_fee = lightning_fee
        self.banker_commission = banker_commission
        self.kelly_fraction = kelly_fraction
        self.min_ev = min_ev

        # Session statistics
        self.wins = 0
        self.losses = 0
        self.current_streak = 0
        self.streak_type: Optional[str] = None  # 'win' or 'loss'

        logger.info(
            f"✅ BankrollManager initialized: "
            f"bankroll={initial_bankroll}, fee={lightning_fee*100}%, "
            f"kelly={kelly_fraction*100}%, min_ev={min_ev*100}%"
        )

    def calculate_ev(
        self,
        prediction: str,
        confidence: float,
        avg_multiplier: float
    ) -> float:
        """
        Calculate Expected Value for a prediction

        Args:
            prediction: 'Player' or 'Banker'
            confidence: Win probability (0.0 to 1.0)
            avg_multiplier: Average Lightning multiplier

        Returns:
            Expected Value
        """
        if prediction == "Player":
            ev = calculate_player_ev(confidence, avg_multiplier, self.lightning_fee)
        elif prediction == "Banker":
            ev = calculate_banker_ev(
                confidence,
                avg_multiplier,
                self.lightning_fee,
                self.banker_commission
            )
        else:
            # Tie or other - not recommended
            ev = -1.0

        return ev

    def calculate_kelly(self, ev: float, odds: float) -> float:
        """
        Calculate Kelly Criterion bet size

        Kelly formula: f = (bp - q) / b
        Where:
        - b = odds (decimal odds - 1)
        - p = probability of winning
        - q = probability of losing (1 - p)

        Args:
            ev: Expected value
            odds: Decimal odds (e.g., 2.0 for even money)

        Returns:
            Fraction of bankroll to bet (capped at 10%)
        """
        if ev <= 0 or odds <= 1.0:
            return 0.0

        # Derive probability from EV and odds
        # For simplicity, use EV to estimate edge
        # edge = ev / (odds - 1)
        b = odds - 1
        edge = ev

        # Kelly: f = edge / b
        kelly = edge / b if b > 0 else 0.0

        # Apply Kelly fraction (e.g., 25% Kelly)
        fractional_kelly = kelly * self.kelly_fraction

        # Cap at 10% of bankroll for safety
        max_bet_fraction = 0.10
        final_kelly = min(fractional_kelly, max_bet_fraction)

        return max(0.0, final_kelly)

    def get_signal(
        self,
        prediction: str,
        confidence: float,
        avg_multiplier: float
    ) -> Dict:
        """
        Generate betting signal based on EV and Kelly criterion

        Args:
            prediction: 'Player' or 'Banker'
            confidence: Win probability (0.0 to 1.0)
            avg_multiplier: Average Lightning multiplier

        Returns:
            Dictionary with:
            - signal: "APOSTAR" or "SALTAR"
            - ev: Expected value
            - kelly_bet: Kelly bet as fraction of bankroll
            - recommended_amount: Actual bet amount in currency
            - reason: Explanation
        """
        ev = self.calculate_ev(prediction, confidence, avg_multiplier)

        # Check if EV is positive and meets minimum threshold
        if ev < self.min_ev:
            return {
                'signal': 'SALTAR',
                'ev': ev,
                'ev_formatted': format_ev(ev),
                'kelly_bet': 0.0,
                'recommended_amount': 0.0,
                'reason': f'EV negativo o insuficiente (EV={format_ev(ev)}, min={self.min_ev:.2%})'
            }

        # Calculate effective odds
        if prediction == "Player":
            effective_payout = (1 + avg_multiplier) * (1 - self.lightning_fee)
        elif prediction == "Banker":
            effective_payout = (
                (1 + avg_multiplier)
                * (1 - self.lightning_fee)
                * (1 - self.banker_commission)
            )
        else:
            effective_payout = 1.0

        odds = 1.0 + effective_payout  # Decimal odds

        # Calculate Kelly bet
        kelly_fraction = self.calculate_kelly(ev, odds)
        recommended_amount = kelly_fraction * self.current_bankroll

        return {
            'signal': 'APOSTAR',
            'ev': ev,
            'ev_formatted': format_ev(ev),
            'kelly_bet': kelly_fraction,
            'kelly_pct': kelly_fraction * 100,
            'recommended_amount': recommended_amount,
            'reason': f'EV positivo: {format_ev(ev)} | Kelly: {kelly_fraction:.1%}'
        }

    def record_result(self, won: bool, amount: float) -> None:
        """
        Record bet result and update bankroll

        Args:
            won: Whether the bet won
            amount: Net profit/loss amount (positive = profit, negative = loss)
        """
        if won:
            self.wins += 1
            self.current_bankroll += amount

            if self.streak_type == 'win':
                self.current_streak += 1
            else:
                self.streak_type = 'win'
                self.current_streak = 1

            logger.info(f"✅ WIN: +{amount:.2f} | Bankroll: {self.current_bankroll:.2f}")
        else:
            self.losses += 1
            self.current_bankroll += amount  # amount is negative for loss

            if self.streak_type == 'loss':
                self.current_streak += 1
            else:
                self.streak_type = 'loss'
                self.current_streak = 1

            logger.info(f"❌ LOSS: {amount:.2f} | Bankroll: {self.current_bankroll:.2f}")

    def get_session_stats(self) -> Dict:
        """
        Get current session statistics

        Returns:
            Dictionary with bankroll, session_pnl, wins, losses, streak
        """
        session_pnl = self.current_bankroll - self.initial_bankroll

        return {
            'bankroll': self.current_bankroll,
            'initial_bankroll': self.initial_bankroll,
            'session_pnl': session_pnl,
            'wins': self.wins,
            'losses': self.losses,
            'total_bets': self.wins + self.losses,
            'win_rate': (
                (self.wins / (self.wins + self.losses) * 100)
                if (self.wins + self.losses) > 0
                else 0.0
            ),
            'streak': self.current_streak,
            'streak_type': self.streak_type or 'none'
        }

    def reset_session(self) -> None:
        """Reset session statistics (not bankroll)"""
        self.wins = 0
        self.losses = 0
        self.current_streak = 0
        self.streak_type = None
        logger.info("🔄 Session statistics reset")

    def set_bankroll(self, new_bankroll: float) -> None:
        """
        Update current bankroll manually

        Args:
            new_bankroll: New bankroll amount
        """
        old_bankroll = self.current_bankroll
        self.current_bankroll = new_bankroll
        logger.info(f"💰 Bankroll updated: {old_bankroll:.2f} → {new_bankroll:.2f}")
