"""
Bankroll Manager with Expected Value calculations for Lightning Baccarat
"""
import logging
from typing import Dict, Optional, Tuple
from src.ev_calculator import calculate_player_ev, calculate_banker_ev

logger = logging.getLogger(__name__)


class BankrollManager:
    """Manages bankroll with Kelly criterion betting and EV tracking"""
    
    def __init__(
        self, 
        initial_bankroll: float,
        lightning_fee: float = 0.50,
        banker_commission: float = 0.05,
        kelly_fraction: float = 0.25,
        min_ev: float = 0.02
    ):
        """
        Initialize Bankroll Manager
        
        Args:
            initial_bankroll: Starting bankroll amount
            lightning_fee: Lightning Baccarat fee (default 0.50 = 50%)
            banker_commission: Banker commission (default 0.05 = 5%)
            kelly_fraction: Fraction of Kelly to use for bet sizing (default 0.25 = 25%)
            min_ev: Minimum EV required to bet (default 0.02 = 2%)
        """
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.lightning_fee = lightning_fee
        self.banker_commission = banker_commission
        self.kelly_fraction = kelly_fraction
        self.min_ev = min_ev
        
        # Session stats
        self.wins = 0
        self.losses = 0
        self.current_streak = 0
        self.max_streak = 0
        self.session_pnl = 0.0
        
    def calculate_ev(self, prediction: str, confidence: float, avg_multiplier: float) -> float:
        """
        Calculate Expected Value for a prediction
        
        Args:
            prediction: "Player" or "Banker"
            confidence: Prediction confidence (0.0 to 1.0)
            avg_multiplier: Average Lightning multiplier
        
        Returns:
            Expected value per unit bet
        """
        pred_lower = prediction.lower()
        
        if pred_lower == "player":
            return calculate_player_ev(confidence, avg_multiplier, self.lightning_fee)
        elif pred_lower == "banker":
            return calculate_banker_ev(
                confidence, 
                avg_multiplier, 
                self.lightning_fee, 
                self.banker_commission
            )
        else:
            # Tie - generally negative EV with Lightning
            return -0.5
    
    def calculate_kelly(self, ev: float, odds: float) -> float:
        """
        Calculate Kelly criterion bet size
        
        Args:
            ev: Expected value per unit
            odds: Decimal odds (e.g., 2.0 for even money)
        
        Returns:
            Fraction of bankroll to bet (Kelly %)
        """
        if ev <= 0 or odds <= 1:
            return 0.0
        
        # Kelly formula: f = (odds * p - 1) / (odds - 1)
        # Where p = (ev + 1) / odds (implied probability for +EV)
        # Simplified: f = ev / (odds - 1)
        kelly_pct = ev / (odds - 1) if odds > 1 else 0
        
        # Apply fractional Kelly for safety
        kelly_pct = kelly_pct * self.kelly_fraction
        
        # Cap at 10% of bankroll for safety
        return min(kelly_pct, 0.10)
    
    def get_signal(
        self, 
        prediction: str, 
        confidence: float, 
        avg_multiplier: float
    ) -> Dict:
        """
        Get betting signal with EV and Kelly sizing
        
        Args:
            prediction: "Player" or "Banker"
            confidence: Prediction confidence (0.0 to 1.0)
            avg_multiplier: Average Lightning multiplier
        
        Returns:
            Dictionary with signal, ev, kelly_bet, recommended_amount
        """
        # Calculate EV
        ev = self.calculate_ev(prediction, confidence, avg_multiplier)
        
        # Determine if we should bet
        should_bet = ev >= self.min_ev
        
        # Calculate Kelly bet sizing if we should bet
        if should_bet:
            # Estimate effective odds based on prediction and multiplier
            pred_lower = prediction.lower()
            if pred_lower == "player":
                # Player pays (1 + avg_mult) * (1 - fee) : 1
                payout = (1 + avg_multiplier) * (1 - self.lightning_fee)
                odds = payout + 1  # Decimal odds
            elif pred_lower == "banker":
                # Banker pays (1 + avg_mult) * (1 - fee) * (1 - commission) : 1
                payout = (1 + avg_multiplier) * (1 - self.lightning_fee) * (1 - self.banker_commission)
                odds = payout + 1
            else:
                odds = 1.0
            
            kelly_pct = self.calculate_kelly(ev, odds)
            recommended_amount = self.current_bankroll * kelly_pct
        else:
            kelly_pct = 0.0
            recommended_amount = 0.0
        
        return {
            'signal': 'APOSTAR' if should_bet else 'SALTAR',
            'ev': ev,
            'kelly_bet': kelly_pct,
            'recommended_amount': recommended_amount
        }
    
    def record_result(self, won: bool, amount: float) -> None:
        """
        Record a bet result
        
        Args:
            won: Whether the bet won
            amount: Amount won (positive) or lost (negative)
        """
        if won:
            self.wins += 1
            self.current_streak = max(1, self.current_streak + 1)
            self.max_streak = max(self.max_streak, self.current_streak)
        else:
            self.losses += 1
            self.current_streak = min(-1, self.current_streak - 1)
        
        self.current_bankroll += amount
        self.session_pnl += amount
        
        logger.info(
            f"Result recorded: {'WIN' if won else 'LOSS'}, "
            f"Amount: {amount:+.2f}, "
            f"Bankroll: {self.current_bankroll:.2f}"
        )
    
    def get_session_stats(self) -> Dict:
        """
        Get session statistics
        
        Returns:
            Dictionary with bankroll, session_pnl, wins, losses, streak
        """
        total_bets = self.wins + self.losses
        win_rate = (self.wins / total_bets * 100) if total_bets > 0 else 0
        roi = (self.session_pnl / self.initial_bankroll * 100) if self.initial_bankroll > 0 else 0
        
        return {
            'bankroll': self.current_bankroll,
            'session_pnl': self.session_pnl,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate,
            'current_streak': self.current_streak,
            'max_streak': self.max_streak,
            'roi': roi,
            'total_bets': total_bets
        }
