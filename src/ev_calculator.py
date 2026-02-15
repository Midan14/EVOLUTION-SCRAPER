"""
Expected Value (EV) Calculator for Lightning Baccarat
Pure utility functions for EV calculations
"""
import logging

logger = logging.getLogger(__name__)


def calculate_player_ev(confidence: float, avg_multiplier: float, fee: float = 0.50) -> float:
    """
    Calculate Expected Value for Player bet with Lightning fee
    
    Formula: EV = (confidence) * (1 + avg_multiplier) * (1 - fee) - (1 - confidence)
    
    Args:
        confidence: Prediction confidence (0.0 to 1.0)
        avg_multiplier: Average Lightning multiplier
        fee: Lightning fee (default 0.50 = 50%)
    
    Returns:
        Expected value per unit bet
    """
    # Win: get back (1 + avg_multiplier) * (1 - fee)
    # Lose: lose 1
    win_payout = (1 + avg_multiplier) * (1 - fee)
    ev = confidence * win_payout - (1 - confidence) * 1
    return ev


def calculate_banker_ev(confidence: float, avg_multiplier: float, fee: float = 0.50, commission: float = 0.05) -> float:
    """
    Calculate Expected Value for Banker bet with Lightning fee and banker commission
    
    Formula: EV = (confidence) * (1 + avg_multiplier) * (1 - fee) * (1 - commission) - (1 - confidence)
    
    Args:
        confidence: Prediction confidence (0.0 to 1.0)
        avg_multiplier: Average Lightning multiplier
        fee: Lightning fee (default 0.50 = 50%)
        commission: Banker commission (default 0.05 = 5%)
    
    Returns:
        Expected value per unit bet
    """
    # Win: get back (1 + avg_multiplier) * (1 - fee) * (1 - commission)
    # Lose: lose 1
    win_payout = (1 + avg_multiplier) * (1 - fee) * (1 - commission)
    ev = confidence * win_payout - (1 - confidence) * 1
    return ev


def min_confidence_for_positive_ev(prediction: str, avg_multiplier: float, fee: float = 0.50) -> float:
    """
    Calculate minimum confidence needed for positive EV
    
    Args:
        prediction: "Player" or "Banker"
        avg_multiplier: Average Lightning multiplier
        fee: Lightning fee (default 0.50 = 50%)
    
    Returns:
        Minimum confidence (0.0 to 1.0) needed for positive EV
    """
    if prediction.lower() == "player":
        # EV > 0 when: confidence * (1 + avg_mult) * (1 - fee) > (1 - confidence)
        # confidence * win_payout + confidence > 1
        # confidence > 1 / (1 + win_payout)
        win_payout = (1 + avg_multiplier) * (1 - fee)
        min_conf = 1 / (1 + win_payout)
    elif prediction.lower() == "banker":
        # Same calculation but with commission
        win_payout = (1 + avg_multiplier) * (1 - fee) * (1 - 0.05)
        min_conf = 1 / (1 + win_payout)
    else:
        # Tie - not recommended
        return 0.9  # Very high threshold for tie
    
    return min_conf


def format_ev(ev_value: float) -> str:
    """
    Format EV value for display
    
    Args:
        ev_value: EV value
    
    Returns:
        Formatted string like "+0.15" or "-0.23"
    """
    sign = "+" if ev_value >= 0 else ""
    return f"{sign}{ev_value:.2f}"
