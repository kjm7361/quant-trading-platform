# strategy_store.py — correctly-spelled alias for the legacy stratergy_store.py
# Import everything from the original so existing code can migrate to this name.
from stratergy_store import (   # noqa: F401
    save_strategy,
    load_strategies,
    get_user_strategies,
    create_strategy,
    get_strategy,
    save_backtest,
    save_portfolio,
)
