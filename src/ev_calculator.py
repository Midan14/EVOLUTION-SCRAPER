"""
EV (Expected Value) Calculator for Lightning Baccarat
Pure functions for EV calculations
"""


def calculate_player_ev(confidence: float, avg_multiplier: float, fee: float = 0.50) -> float:
    """
    Calculate Expected Value for Player bet

    Formula: EV = confidence * (1 + avg_multiplier) * (1 - fee) - (1 - confidence)

    Args:
        confidence: Win probability as decimal (0.0 to 1.0).
                   Should be a probability derived from model predictions.
                   Example: 0.60 for 60% confidence
        avg_multiplier: Average Lightning multiplier
        fee: Lightning fee (default 0.50 = 50%)

    Returns:
        Expected Value (positive = profitable, negative = unprofitable)
    """
    win_return = (1 + avg_multiplier) * (1 - fee)
    ev = confidence * win_return - (1 - confidence)
    return ev


def calculate_banker_ev(
    confidence: float,
    avg_multiplier: float,
    fee: float = 0.50,
    commission: float = 0.05
) -> float:
    """
    Calculate Expected Value for Banker bet

    Formula:
    EV = confidence * (1 + avg_mult) * (1 - fee) * (1 - comm) - (1 - confidence)

    Args:
        confidence: Win probability (0.0 to 1.0)
        avg_multiplier: Average Lightning multiplier
        fee: Lightning fee (default 0.50 = 50%)
        commission: Banker commission (default 0.05 = 5%)

    Returns:
        Expected Value (positive = profitable, negative = unprofitable)
    """
    win_return = (1 + avg_multiplier) * (1 - fee) * (1 - commission)
    ev = confidence * win_return - (1 - confidence)
    return ev


def min_confidence_for_positive_ev(
    prediction: str,
    avg_multiplier: float,
    fee: float = 0.50,
    commission: float = 0.05
) -> float:
    """
    Calculate minimum confidence needed for positive EV

    Solves for confidence where EV = 0:
    - Player: confidence * (1 + avg_mult) * (1 - fee) - (1 - confidence) = 0
    - Banker: confidence * (1 + avg_mult) * (1 - fee) * (1 - commission) - (1 - confidence) = 0

    Args:
        prediction: 'Player' or 'Banker'
        avg_multiplier: Average Lightning multiplier
        fee: Lightning fee (default 0.50 = 50%)
        commission: Banker commission (default 0.05 = 5%)

    Returns:
        Minimum confidence required (0.0 to 1.0)
    """
    if prediction == "Player":
        win_return = (1 + avg_multiplier) * (1 - fee)
    elif prediction == "Banker":
        win_return = (1 + avg_multiplier) * (1 - fee) * (1 - commission)
    else:
        # Tie or unknown - use conservative estimate
        win_return = 1.0

    # Solve: confidence * win_return - (1 - confidence) = 0
    # confidence * win_return + confidence = 1
    # confidence * (win_return + 1) = 1
    # confidence = 1 / (win_return + 1)

    if win_return + 1 == 0:
        return 1.0  # Edge case

    min_conf = 1.0 / (win_return + 1)

    # Clamp to [0, 1]
    return max(0.0, min(1.0, min_conf))


def format_ev(ev_value: float) -> str:
    """
    Format EV value as string with sign

    Args:
        ev_value: Expected Value

    Returns:
        Formatted string like "+0.15" or "-0.23"
    """
    if ev_value >= 0:
        return f"+{ev_value:.2f}"
    else:
        return f"{ev_value:.2f}"


def calculate_payout_with_multiplier(
    bet_amount: float,
    win: bool,
    multiplier: float,
    prediction: str,
    fee: float = 0.50,
    commission: float = 0.05
) -> float:
    """
    Calculate actual payout including Lightning multiplier

    Args:
        bet_amount: Amount wagered
        win: Whether the bet won
        multiplier: Lightning multiplier applied (1.0 if none)
        prediction: 'Player' or 'Banker'
        fee: Lightning fee
        commission: Banker commission

    Returns:
        Net payout (positive = profit, negative = loss)
    """
    if not win:
        return -bet_amount

    # Win return
    if prediction == "Player":
        gross_return = bet_amount * (1 + multiplier) * (1 - fee)
    elif prediction == "Banker":
        gross_return = bet_amount * (1 + multiplier) * (1 - fee) * (1 - commission)
    else:
        gross_return = bet_amount  # Default case

    net_profit = gross_return - bet_amount
    return net_profit
