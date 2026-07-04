"""
core/context.py
StrategyContext — a single object that carries all backtest inputs and outputs
across pages through Streamlit session state.

Pages that produce context (backtest):
    from core.context import StrategyContext, save_context
    ctx = StrategyContext(...)
    save_context(ctx)

Pages that consume context (live signals, trading bot, comparison):
    from core.context import load_context
    ctx = load_context()
    if ctx and ctx.is_complete():
        ...use ctx.net_returns, ctx.positions, etc...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd
import streamlit as st

_SESSION_KEY = "_strategy_context"


@dataclass
class StrategyContext:
    # ── Universe & date range ─────────────────────────────────────────────────
    tickers:       List[str]              = field(default_factory=list)
    start_date:    str                    = ""
    end_date:      str                    = ""

    # ── Raw data ──────────────────────────────────────────────────────────────
    prices:        Optional[pd.DataFrame] = None

    # ── Pipeline outputs ──────────────────────────────────────────────────────
    signal:        Optional[pd.DataFrame] = None   # composite cross-sectional scores
    positions:     Optional[pd.DataFrame] = None   # normalized long-short weights
    gross_returns: Optional[pd.Series]   = None
    net_returns:   Optional[pd.Series]   = None    # after transaction costs
    equity_curve:  Optional[pd.Series]   = None

    # ── Strategy metadata ─────────────────────────────────────────────────────
    strategy_name: str                    = "Unnamed"
    signals_used:  List[str]              = field(default_factory=list)
    cost_bps:      float                  = 10.0
    rebalance_freq: str                   = "M"

    # ── Optional performance metrics (populated by backtest page) ─────────────
    sharpe:        Optional[float]        = None
    max_drawdown:  Optional[float]        = None
    avg_turnover:  Optional[float]        = None
    alpha_annual:  Optional[float]        = None
    beta:          Optional[float]        = None
    mean_ic:       Optional[float]        = None    # populated after IC analysis

    def is_complete(self) -> bool:
        """True when the full backtest pipeline has been run."""
        return (
            self.net_returns is not None
            and self.equity_curve is not None
            and len(self.net_returns) > 0
        )

    def summary(self) -> dict:
        """Flat dict of key metrics for display."""
        return {
            "Strategy":       self.strategy_name,
            "Signals":        ", ".join(self.signals_used),
            "Tickers":        len(self.tickers),
            "Start":          self.start_date,
            "End":            self.end_date,
            "Cost (bps)":     self.cost_bps,
            "Rebalance":      self.rebalance_freq,
            "Sharpe":         self.sharpe,
            "Max DD":         self.max_drawdown,
            "Avg Turnover":   self.avg_turnover,
            "Alpha (annual)": self.alpha_annual,
            "Beta":           self.beta,
            "Mean IC":        self.mean_ic,
        }


# ── Session helpers ───────────────────────────────────────────────────────────

def save_context(ctx: StrategyContext) -> None:
    """Persist context to Streamlit session state."""
    st.session_state[_SESSION_KEY] = ctx


def load_context() -> Optional[StrategyContext]:
    """Load context from session state; returns None if not yet set."""
    return st.session_state.get(_SESSION_KEY)


def clear_context() -> None:
    """Remove context (call before a new backtest run to avoid stale data)."""
    st.session_state.pop(_SESSION_KEY, None)


def context_is_ready() -> bool:
    """Quick check without loading the full object."""
    ctx = load_context()
    return ctx is not None and ctx.is_complete()
