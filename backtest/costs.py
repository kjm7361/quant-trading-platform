"""
backtest/costs.py
Two-component realistic transaction cost model.

Component 1 — Spread cost
    Every time you trade a unit of weight, you cross half the bid-ask spread.
    cost = (spread_bps / 10_000) × |Δw|

Component 2 — Market impact  (optional, requires lambda_ > 0)
    Almgren-Chriss-style quadratic impact: the larger the trade relative to
    average daily volume, the more you move the price against yourself.
    cost = lambda_ × Δw²

Backward-compatible with old call signature:
    apply_transaction_costs(positions, cost_rate)
"""

from __future__ import annotations

import pandas as pd


def apply_transaction_costs(
    positions: pd.DataFrame,
    cost_rate: float = 0.001,
    prices: pd.DataFrame | None = None,
    spread_bps: float = 5.0,
    market_impact_lambda: float = 0.0,
) -> pd.Series:
    """
    Compute per-period transaction costs.

    Parameters
    ----------
    positions : pd.DataFrame
        Portfolio weights (date × ticker).
    cost_rate : float
        Legacy flat cost rate.  Used only when prices is None.
    prices : pd.DataFrame or None
        If provided, uses the two-component model (spread + impact).
        If None, falls back to legacy flat model: turnover × cost_rate.
    spread_bps : float
        One-way bid-ask spread in basis points (default 5 bps = 0.05 %).
        Half is paid on each leg → full round-trip = spread_bps bps.
    market_impact_lambda : float
        Kyle's λ-style impact coefficient.  Set > 0 to enable impact costs.
        Units: price impact per unit of signed order flow (same as Kyle's λ).
        Typical values for large-cap equities: 1e-6 to 1e-5.

    Returns
    -------
    pd.Series
        Cost per period (same index as positions), subtracted from gross returns.
    """
    turnover = positions.diff().abs().sum(axis=1)

    # ── Legacy mode (no prices supplied) ─────────────────────────────────────
    if prices is None:
        return (turnover * cost_rate).fillna(0.0)

    # ── Two-component model ───────────────────────────────────────────────────

    # Component 1: explicit spread cost
    #   (spread_bps / 10_000) represents the one-way half-spread cost per unit
    spread_cost = turnover * (spread_bps / 10_000)

    # Component 2: market impact (quadratic, Almgren-Chriss inspired)
    if market_impact_lambda > 0:
        delta = positions.diff().fillna(0.0)
        impact = (delta ** 2).sum(axis=1) * market_impact_lambda
    else:
        impact = pd.Series(0.0, index=positions.index)

    total = (spread_cost + impact).reindex(positions.index).fillna(0.0)
    return total


def cost_breakdown(
    positions: pd.DataFrame,
    spread_bps: float = 5.0,
    market_impact_lambda: float = 0.0,
) -> pd.DataFrame:
    """
    Return a DataFrame with spread_cost, impact_cost, and total_cost columns
    for diagnostic analysis.
    """
    delta    = positions.diff().fillna(0.0)
    turnover = delta.abs().sum(axis=1)

    spread = turnover * (spread_bps / 10_000)

    if market_impact_lambda > 0:
        impact = (delta ** 2).sum(axis=1) * market_impact_lambda
    else:
        impact = pd.Series(0.0, index=positions.index)

    return pd.DataFrame({
        "spread_cost": spread,
        "impact_cost": impact,
        "total_cost":  spread + impact,
        "turnover":    turnover,
    })
