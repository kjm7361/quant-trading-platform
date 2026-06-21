from __future__ import annotations

import streamlit as st

# Graceful import — alpaca-py may not be installed
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    _ALPACA_AVAILABLE = True
except ImportError:
    _ALPACA_AVAILABLE = False


def alpaca_available() -> bool:
    """True if alpaca-py is installed AND secrets are configured."""
    if not _ALPACA_AVAILABLE:
        return False
    try:
        _ = st.secrets["ALPACA_API_KEY"]
        _ = st.secrets["ALPACA_SECRET_KEY"]
        return True
    except (KeyError, FileNotFoundError):
        return False


def _get_bool(x) -> bool:
    if isinstance(x, bool):
        return x
    return str(x).strip().lower() in ("true", "1", "yes")


@st.cache_resource
def get_trading_client():
    if not _ALPACA_AVAILABLE:
        raise RuntimeError(
            "alpaca-py is not installed. Run `pip install alpaca-py` and restart."
        )
    key    = st.secrets["ALPACA_API_KEY"]
    secret = st.secrets["ALPACA_SECRET_KEY"]
    paper  = _get_bool(st.secrets.get("ALPACA_PAPER", True))
    return TradingClient(key, secret, paper=paper)


def get_account():
    return get_trading_client().get_account()


def list_positions():
    return get_trading_client().get_all_positions()


def list_orders(status: str = "all", limit: int = 50):
    return get_trading_client().get_orders(status=status, limit=limit)


def submit_market_order(symbol: str, qty: float, side: str):
    c    = get_trading_client()
    s    = OrderSide.BUY if str(side).lower() == "buy" else OrderSide.SELL
    req  = MarketOrderRequest(
        symbol=str(symbol).upper().strip(),
        qty=float(qty),
        side=s,
        time_in_force=TimeInForce.DAY,
    )
    return c.submit_order(order_data=req)


def submit_limit_order(symbol: str, qty: float, side: str, limit_price: float):
    c    = get_trading_client()
    s    = OrderSide.BUY if str(side).lower() == "buy" else OrderSide.SELL
    req  = LimitOrderRequest(
        symbol=str(symbol).upper().strip(),
        qty=float(qty),
        side=s,
        time_in_force=TimeInForce.DAY,
        limit_price=float(limit_price),
    )
    return c.submit_order(order_data=req)
