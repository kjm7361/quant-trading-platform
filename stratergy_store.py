# BACKWARD-COMPATIBILITY LAYER

from storage.strategies.access import (
    create_strategy,
    list_strategies,
    get_strategy
)

from storage.backtests.access import save_backtest
from storage.portfolios.access import save_portfolio


# -----------------------------
# OLD API (kept so app.py doesn't break)
# -----------------------------

def save_strategy(name, payload):
    """
    Legacy wrapper. Creates a strategy and saves one backtest.
    """
    strategy_id = create_strategy(
        name=name,
        signals=payload.get("signals", []),
        user_id=payload.get("user_id", "default_user")
    )

    save_backtest(
        strategy_id=strategy_id,
        metrics=payload.get("metrics", {}),
        start=payload.get("start", "unknown"),
        end=payload.get("end", "unknown")
    )

    return strategy_id


def load_strategies():
    return list_strategies()


def get_user_strategies(user_id):
    return list_strategies(user_id)


# -----------------------------
# NEW API (preferred)
# -----------------------------

__all__ = [
    "save_strategy",
    "load_strategies",
    "get_user_strategies",
    "create_strategy",
    "get_strategy",
    "save_backtest",
    "save_portfolio",
]
