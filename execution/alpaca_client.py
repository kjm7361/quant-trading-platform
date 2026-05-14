from __future__ import annotations

import streamlit as st
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce


def _get_bool(x):
    if type(x) == bool:
        return x
    s = str(x).strip().lower()
    return (s == "true") or (s == "1") or (s == "yes")


@st.cache_resource
def get_trading_client():
    key = st.secrets["ALPACA_API_KEY"]
    secret = st.secrets["ALPACA_SECRET_KEY"]
    paper = _get_bool(st.secrets.get("ALPACA_PAPER", True))
    return TradingClient(key, secret, paper=paper)


def get_account():
    c = get_trading_client()
    return c.get_account()


def list_positions():
    c = get_trading_client()
    return c.get_all_positions()


def list_orders(status="all", limit=50):
    c = get_trading_client()
    return c.get_orders(status=status, limit=limit)


def submit_market_order(symbol, qty, side):
    c = get_trading_client()

    if str(side).lower() == "buy":
        s = OrderSide.BUY
    else:
        s = OrderSide.SELL

    req = MarketOrderRequest(
        symbol=str(symbol).upper().strip(),
        qty=float(qty),
        side=s,
        time_in_force=TimeInForce.DAY
    )
    return c.submit_order(order_data=req)


def submit_limit_order(symbol, qty, side, limit_price):
    c = get_trading_client()

    if str(side).lower() == "buy":
        s = OrderSide.BUY
    else:
        s = OrderSide.SELL

    req = LimitOrderRequest(
        symbol=str(symbol).upper().strip(),
        qty=float(qty),
        side=s,
        time_in_force=TimeInForce.DAY,
        limit_price=float(limit_price)
    )
    return c.submit_order(order_data=req)