"""
core/state.py
Centralised session-state management for the Quant Terminal platform.
All pages import from here so state keys stay consistent.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
from datetime import datetime

_DEFAULTS: dict = {
    "positions":           {},
    "trade_history":       [],
    "equity_curve":        None,
    "strategy_returns":    None,
    "initial_capital":     100_000.0,
    "active_signals":      {},
    "risk_metrics":        {},
    "market_regime":       "UNKNOWN",
    "alerts":              [],
    "ml_signals":          {},
    "factor_scores":       {},
    "sentiment_scores":    {},
    "kill_switch":         False,
    "kill_switch_reasons": [],
    "broker_mode":         "SIMULATED",
    "logged_in":           False,
    "username":            "guest",
}


def bootstrap() -> None:
    """Idempotent: add any missing keys with their defaults."""
    for key, default in _DEFAULTS.items():
        if key not in st.session_state:
            if isinstance(default, (dict, list)):
                st.session_state[key] = type(default)()
            else:
                st.session_state[key] = default


# ── Positions ─────────────────────────────────────────────────────────────────
def get_positions() -> dict:
    bootstrap()
    return st.session_state.get("positions", {})


def set_positions(positions: dict) -> None:
    st.session_state["positions"] = positions


# ── Trade History ─────────────────────────────────────────────────────────────
def get_trade_history() -> list:
    bootstrap()
    return st.session_state.get("trade_history", [])


def add_trade(symbol: str, side: str, qty: float, price: float) -> None:
    hist = get_trade_history()
    hist.append({
        "ts": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
    })
    st.session_state["trade_history"] = hist[-500:]


# ── Equity Curve ──────────────────────────────────────────────────────────────
def get_equity_curve():
    bootstrap()
    return st.session_state.get("equity_curve")


def set_equity_curve(ec) -> None:
    st.session_state["equity_curve"] = ec


# ── Strategy Returns ──────────────────────────────────────────────────────────
def get_strategy_returns():
    bootstrap()
    return st.session_state.get("strategy_returns")


def set_strategy_returns(rets) -> None:
    st.session_state["strategy_returns"] = rets


# ── Active Signals ────────────────────────────────────────────────────────────
def get_active_signals() -> dict:
    bootstrap()
    return st.session_state.get("active_signals", {})


def set_signal(symbol: str, signal: str, confidence: float, source: str = "unknown") -> None:
    sigs = get_active_signals()
    sigs[symbol] = {
        "signal":     signal,
        "confidence": round(float(confidence), 4),
        "source":     source,
        "ts":         datetime.utcnow().isoformat(),
    }
    st.session_state["active_signals"] = sigs


# ── Risk Metrics ──────────────────────────────────────────────────────────────
def get_risk_metrics() -> dict:
    bootstrap()
    return st.session_state.get("risk_metrics", {})


def set_risk_metrics(metrics: dict) -> None:
    st.session_state["risk_metrics"] = metrics


# ── Market Regime ─────────────────────────────────────────────────────────────
def get_market_regime() -> str:
    bootstrap()
    return st.session_state.get("market_regime", "UNKNOWN")


def set_market_regime(regime: str) -> None:
    st.session_state["market_regime"] = regime


# ── Alerts ────────────────────────────────────────────────────────────────────
def get_alerts() -> list:
    bootstrap()
    return st.session_state.get("alerts", [])


def add_alert(level: str, message: str) -> None:
    alerts = get_alerts()
    alerts.append({
        "ts":      datetime.utcnow().isoformat(),
        "level":   level,
        "message": message,
    })
    st.session_state["alerts"] = alerts[-100:]


# ── ML Signals ────────────────────────────────────────────────────────────────
def get_ml_signals() -> dict:
    bootstrap()
    return st.session_state.get("ml_signals", {})


def set_ml_signal(symbol: str, prediction: str, confidence: float) -> None:
    sigs = get_ml_signals()
    sigs[symbol] = {
        "prediction": prediction,
        "confidence": round(float(confidence), 4),
        "ts":         datetime.utcnow().isoformat(),
    }
    st.session_state["ml_signals"] = sigs


# ── Factor Scores ─────────────────────────────────────────────────────────────
def get_factor_scores() -> dict:
    bootstrap()
    return st.session_state.get("factor_scores", {})


def set_factor_scores(scores: dict) -> None:
    st.session_state["factor_scores"] = scores


# ── Sentiment Scores ──────────────────────────────────────────────────────────
def get_sentiment_scores() -> dict:
    bootstrap()
    return st.session_state.get("sentiment_scores", {})


def set_sentiment_scores(scores: dict) -> None:
    st.session_state["sentiment_scores"] = scores


# ── Kill Switch ───────────────────────────────────────────────────────────────
def is_kill_switch_active() -> bool:
    bootstrap()
    return bool(st.session_state.get("kill_switch", False))


def set_kill_switch(active: bool, reason: str = "") -> None:
    st.session_state["kill_switch"] = active
    if active and reason:
        reasons = st.session_state.get("kill_switch_reasons", [])
        reasons.append(reason)
        st.session_state["kill_switch_reasons"] = reasons[-10:]


# ── Broker Mode ───────────────────────────────────────────────────────────────
def get_broker_mode() -> str:
    bootstrap()
    return st.session_state.get("broker_mode", "SIMULATED")


def set_broker_mode(mode: str) -> None:
    st.session_state["broker_mode"] = mode


# ── Platform Summary ──────────────────────────────────────────────────────────
def get_platform_summary() -> dict:
    """Flat dict of key platform KPIs for the Command Center dashboard."""
    bootstrap()

    ec   = get_equity_curve()
    rets = get_strategy_returns()
    rm   = get_risk_metrics()
    sigs = get_active_signals()
    ml   = get_ml_signals()
    sent = get_sentiment_scores()

    port_value = float(st.session_state.get("initial_capital", 100_000))
    if ec is not None and hasattr(ec, "iloc") and len(ec) > 0:
        port_value = float(ec.iloc[-1])

    daily_pnl_pct = 0.0
    if rets is not None and hasattr(rets, "iloc") and len(rets) > 0:
        daily_pnl_pct = float(rets.iloc[-1]) * 100

    # Strongest signal (highest confidence across all sources)
    all_sigs: dict[str, tuple] = {}
    for sym, v in sigs.items():
        all_sigs[sym] = (v.get("signal", "HOLD"), v.get("confidence", 0.0), v.get("source", ""))
    for sym, v in ml.items():
        if sym not in all_sigs or v.get("confidence", 0) > all_sigs[sym][1]:
            all_sigs[sym] = (v.get("prediction", "HOLD"), v.get("confidence", 0.0), "ML")

    strongest = None
    if all_sigs:
        sym = max(all_sigs, key=lambda s: all_sigs[s][1])
        sig, conf, src = all_sigs[sym]
        strongest = {"symbol": sym, "signal": sig, "confidence": conf, "source": src}

    avg_sentiment = 0.0
    if sent:
        avg_sentiment = sum(v.get("score", 0) for v in sent.values()) / len(sent)

    return {
        "portfolio_value":  port_value,
        "daily_pnl_pct":    daily_pnl_pct,
        "sharpe":           rm.get("sharpe", 0.0),
        "max_dd":           rm.get("max_dd", 0.0),
        "market_regime":    get_market_regime(),
        "kill_switch":      is_kill_switch_active(),
        "broker_mode":      get_broker_mode(),
        "strongest_signal": strongest,
        "avg_sentiment":    avg_sentiment,
        "alert_count":      len(get_alerts()),
        "position_count":   len(get_positions()),
    }
