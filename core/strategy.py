"""
core/strategy.py
Strategy abstract base class + concrete factor implementations.

All strategy objects share the same interface:
  strategy.generate_signal(prices, **kwargs) -> pd.DataFrame (date × ticker scores)
  strategy.name  -> str
  strategy.description -> str

This lets backtest, trading bot, and live signal pages all consume
strategies through a single contract instead of calling loose functions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


class BaseStrategy(ABC):
    """Abstract base for all factor strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short human-readable strategy name."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """One-sentence description for display in the UI."""
        ...

    @abstractmethod
    def generate_signal(self, prices: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Compute raw signal scores.

        Parameters
        ----------
        prices : pd.DataFrame
            Close prices — index=date, columns=tickers.
        **kwargs
            Strategy-specific fundamentals (book_equity, market_cap, etc.).

        Returns
        -------
        pd.DataFrame
            Same shape as prices: higher value = stronger positive signal.
        """
        ...

    def rank(self, signal: pd.DataFrame) -> pd.DataFrame:
        """Cross-sectional percentile rank per date (0 = lowest, 1 = highest)."""
        return signal.rank(axis=1, pct=True)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"


# ── Concrete implementations ──────────────────────────────────────────────────

class MomentumStrategy(BaseStrategy):
    """
    Cross-sectional momentum: cumulative return from t-lookback to t-skip.
    Classic Jegadeesh & Titman (1993): lookback=12, skip=1 (months → days here).
    """

    def __init__(self, lookback: int = 12, skip: int = 1):
        self.lookback = lookback
        self.skip = skip

    @property
    def name(self) -> str:
        return f"Momentum ({self.lookback}-{self.skip})"

    @property
    def description(self) -> str:
        return (
            f"Cross-sectional {self.lookback}-{self.skip} month momentum signal. "
            "Buys past winners, shorts past losers (Jegadeesh & Titman 1993)."
        )

    def generate_signal(self, prices: pd.DataFrame, **kwargs) -> pd.DataFrame:
        ret = prices.pct_change()
        skip = max(1, self.skip)
        momentum = (1 + ret).rolling(self.lookback).apply(
            lambda x: x[:-skip].prod() - 1,
            raw=False,
        )
        return momentum


class ValueStrategy(BaseStrategy):
    """Book-to-market ratio (Fama & French 1992). Requires fundamental data."""

    @property
    def name(self) -> str:
        return "Value (B/M)"

    @property
    def description(self) -> str:
        return (
            "Book-to-market ratio. High B/M = value stock. "
            "Requires book_equity and market_cap kwargs."
        )

    def generate_signal(
        self,
        prices: pd.DataFrame,
        book_equity: Optional[pd.DataFrame] = None,
        market_cap: Optional[pd.DataFrame] = None,
        **kwargs,
    ) -> pd.DataFrame:
        if book_equity is None or market_cap is None:
            raise ValueError("ValueStrategy requires book_equity and market_cap DataFrames.")
        mc = market_cap.replace(0, np.nan)
        return book_equity / mc


class ProfitabilityStrategy(BaseStrategy):
    """Gross profitability / market equity (Novy-Marx 2013)."""

    @property
    def name(self) -> str:
        return "Profitability (GP/ME)"

    @property
    def description(self) -> str:
        return (
            "Gross profitability scaled by market equity (Novy-Marx 2013). "
            "Requires gross_profit and market_cap kwargs."
        )

    def generate_signal(
        self,
        prices: pd.DataFrame,
        gross_profit: Optional[pd.DataFrame] = None,
        market_cap: Optional[pd.DataFrame] = None,
        **kwargs,
    ) -> pd.DataFrame:
        if gross_profit is None or market_cap is None:
            raise ValueError("ProfitabilityStrategy requires gross_profit and market_cap DataFrames.")
        mc = market_cap.replace(0, np.nan)
        return gross_profit / mc


class LowVolatilityStrategy(BaseStrategy):
    """
    Low-volatility anomaly: rank stocks by inverse realized volatility.
    Lower vol → higher signal (Ang et al. 2006).
    """

    def __init__(self, window: int = 20):
        self.window = window

    @property
    def name(self) -> str:
        return f"Low Volatility ({self.window}d)"

    @property
    def description(self) -> str:
        return (
            f"Inverse {self.window}-day realized volatility. "
            "Low-vol stocks tend to outperform on a risk-adjusted basis (Ang et al. 2006)."
        )

    def generate_signal(self, prices: pd.DataFrame, **kwargs) -> pd.DataFrame:
        vol = prices.pct_change().rolling(self.window).std()
        return -vol  # negate: lower vol → higher signal


class ShortTermReversalStrategy(BaseStrategy):
    """1-month reversal (Jegadeesh 1990). Short past winners over 1 month."""

    def __init__(self, window: int = 21):
        self.window = window

    @property
    def name(self) -> str:
        return f"Short-Term Reversal ({self.window}d)"

    @property
    def description(self) -> str:
        return (
            f"Negative {self.window}-day return — bets on mean reversion "
            "over a short horizon (Jegadeesh 1990)."
        )

    def generate_signal(self, prices: pd.DataFrame, **kwargs) -> pd.DataFrame:
        ret = prices.pct_change(self.window)
        return -ret  # negate: past losers become buys


class CompositeStrategy(BaseStrategy):
    """
    Weighted combination of any BaseStrategy instances.
    Each sub-signal is first cross-sectionally ranked, then averaged.
    """

    def __init__(
        self,
        strategies: List[BaseStrategy],
        weights: Optional[List[float]] = None,
    ):
        self.strategies = strategies
        n = len(strategies)
        self.weights = weights if weights else [1.0 / n] * n

    @property
    def name(self) -> str:
        return " + ".join(s.name for s in self.strategies)

    @property
    def description(self) -> str:
        return "Composite of: " + ", ".join(s.name for s in self.strategies)

    def generate_signal(self, prices: pd.DataFrame, **kwargs) -> pd.DataFrame:
        ranked: List[pd.DataFrame] = []
        for strat, w in zip(self.strategies, self.weights):
            try:
                sig = strat.generate_signal(prices, **kwargs)
                ranked.append(self.rank(sig) * w)
            except Exception:
                continue
        if not ranked:
            return pd.DataFrame()
        total_w = sum(self.weights[: len(ranked)])
        combined = sum(ranked)
        return combined / total_w if total_w > 0 else combined


# ── Public registry — used by UI dropdowns ────────────────────────────────────

STRATEGY_REGISTRY: Dict[str, BaseStrategy] = {
    "Momentum (12-1)":        MomentumStrategy(lookback=12, skip=1),
    "Momentum (6-1)":         MomentumStrategy(lookback=6,  skip=1),
    "Low Volatility (20d)":   LowVolatilityStrategy(window=20),
    "Low Volatility (60d)":   LowVolatilityStrategy(window=60),
    "Short-Term Reversal":    ShortTermReversalStrategy(window=21),
}
