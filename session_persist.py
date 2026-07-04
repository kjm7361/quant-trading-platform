"""
Persist key session-state values to disk so they survive Streamlit page
refreshes and browser tab switches.

Storage: storage/session_cache.json (JSON, human-readable)

Usage
-----
# After computing equity / returns data:
from session_persist import save_session, restore_session
save_session(equity_curve, strategy_returns, initial_capital)

# At page startup (called automatically by setup_page):
restore_session()   # fills st.session_state if it's empty
"""

import json
import os
import streamlit as st
import pandas as pd
from datetime import datetime

_CACHE_PATH = os.path.join(os.path.dirname(__file__), "storage", "session_cache.json")


def _series_to_dict(s: pd.Series) -> dict:
    """Serialize a pd.Series to a JSON-safe dict."""
    return {
        "values": [float(v) for v in s.values],
        "index":  [str(i) for i in s.index],
    }


def _dict_to_series(d: dict) -> pd.Series:
    """Deserialize a dict back to a pd.Series, restoring a DatetimeIndex if possible."""
    values = d["values"]
    raw_idx = d["index"]
    try:
        idx = pd.to_datetime(raw_idx)
    except Exception:
        idx = raw_idx
    return pd.Series(values, index=idx)


def save_session(
    equity_curve: pd.Series,
    strategy_returns: pd.Series,
    initial_capital: float,
) -> None:
    """Write equity / returns data to disk."""
    try:
        payload = {
            "equity_curve":      _series_to_dict(equity_curve),
            "strategy_returns":  _series_to_dict(strategy_returns),
            "initial_capital":   float(initial_capital),
            "saved_at":          datetime.now().isoformat(timespec="seconds"),
        }
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "w") as f:
            json.dump(payload, f)
    except Exception:
        pass   # never crash a page because of a cache write failure


def restore_session() -> bool:
    """
    Load persisted data into st.session_state if the key is missing.
    Returns True if data was restored, False if nothing was available.
    """
    # Already in session state — nothing to do
    if st.session_state.get("equity_curve") is not None:
        return False

    if not os.path.exists(_CACHE_PATH):
        return False

    try:
        with open(_CACHE_PATH) as f:
            payload = json.load(f)

        equity   = _dict_to_series(payload["equity_curve"])
        returns  = _dict_to_series(payload["strategy_returns"])
        capital  = float(payload.get("initial_capital", 100_000.0))
        saved_at = payload.get("saved_at", "unknown")

        if len(equity) < 2:
            return False

        st.session_state["equity_curve"]      = equity
        st.session_state["strategy_returns"]  = returns
        st.session_state["initial_capital"]   = capital
        st.session_state["_session_restored"] = saved_at
        return True

    except Exception:
        return False


def clear_session_cache() -> None:
    """Delete the cache file (e.g. after account reset)."""
    try:
        if os.path.exists(_CACHE_PATH):
            os.remove(_CACHE_PATH)
    except Exception:
        pass
