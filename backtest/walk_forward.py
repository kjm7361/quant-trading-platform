"""
backtest/walk_forward.py
Walk-forward (out-of-sample) validation engine.

The standard problem with a full-sample backtest is that signals are computed
using data that wasn't available at trade time (look-ahead bias). Walk-forward
fixes this: train on a rolling window, test on the NEXT period only, then slide
forward and repeat.

Usage
-----
    from backtest.walk_forward import walk_forward_backtest

    result = walk_forward_backtest(
        prices          = prices,
        build_signal_fn = lambda p: composite_signal(momentum_signal(p), ...),
        generate_positions_fn = generate_positions,
        compute_returns_fn    = compute_returns,
        apply_costs_fn        = lambda pos: apply_transaction_costs(pos, cost_rate),
        n_train = 252 * 3,   # 3-year training window
        n_test  = 63,        # 1-quarter test window
    )

    oos_returns = result["oos_returns"]   # pd.Series
    fold_stats  = result["fold_stats"]    # list[dict]
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd


def walk_forward_backtest(
    prices: pd.DataFrame,
    build_signal_fn: Callable[[pd.DataFrame], pd.DataFrame],
    generate_positions_fn: Callable[[pd.DataFrame], pd.DataFrame],
    compute_returns_fn: Callable[[pd.DataFrame, pd.DataFrame], pd.Series],
    apply_costs_fn: Callable[[pd.DataFrame], pd.Series],
    n_train: int = 756,   # default: 3 years (252 × 3)
    n_test:  int = 63,    # default: 1 quarter
) -> Dict[str, Any]:
    """
    Expanding or rolling walk-forward backtest.

    Parameters
    ----------
    prices : pd.DataFrame
        Full price history (date × ticker).
    build_signal_fn : callable
        Takes a price DataFrame (train window) → signal DataFrame.
    generate_positions_fn : callable
        Takes signal DataFrame → positions DataFrame.
    compute_returns_fn : callable
        Takes (prices, positions) → raw returns Series.
    apply_costs_fn : callable
        Takes positions → cost Series.
    n_train : int
        Number of trading days in each training window.
    n_test : int
        Number of trading days in each test (OOS) window.

    Returns
    -------
    dict with keys:
        "oos_returns"  : pd.Series — concatenated out-of-sample net returns
        "fold_stats"   : list[dict] — per-fold Sharpe, dates, etc.
        "n_folds"      : int
    """
    prices = prices.copy().dropna(how="all")
    total  = len(prices)

    if total < n_train + n_test:
        return {"oos_returns": pd.Series(dtype=float), "fold_stats": [], "n_folds": 0}

    oos_chunks: List[pd.Series] = []
    fold_stats: List[dict]       = []
    fold = 0
    cursor = n_train

    while cursor + n_test <= total:
        fold += 1
        train_px = prices.iloc[cursor - n_train : cursor]
        test_px  = prices.iloc[cursor : cursor + n_test]

        # ── Train: build signal on historical window only ─────────────────────
        try:
            signal = build_signal_fn(train_px)
        except Exception:
            cursor += n_test
            continue

        if signal is None or (hasattr(signal, "empty") and signal.empty):
            cursor += n_test
            continue

        # Use last period's signal, held constant through the test window
        last_row = signal.iloc[[-1]]
        test_signal = pd.DataFrame(
            np.tile(last_row.values, (len(test_px), 1)),
            index=test_px.index,
            columns=last_row.columns,
        ).reindex(columns=test_px.columns)

        # ── Test: evaluate on unseen data ─────────────────────────────────────
        try:
            positions = generate_positions_fn(test_signal).shift(1).fillna(0.0)
            raw_ret   = compute_returns_fn(test_px, positions)
            costs     = apply_costs_fn(positions)
            net_ret   = (raw_ret - costs).fillna(0.0)
        except Exception:
            cursor += n_test
            continue

        ann_factor = np.sqrt(252)
        net_arr    = net_ret.values
        std        = net_arr.std()
        sharpe_oos = float(net_arr.mean() / std * ann_factor) if std > 0 else 0.0

        eq = (1 + net_ret.fillna(0)).cumprod()
        mdd = float((eq / eq.cummax() - 1).min()) if len(eq) > 0 else 0.0

        oos_chunks.append(net_ret)
        fold_stats.append({
            "Fold":        fold,
            "Train Start": str(train_px.index[0].date()),
            "Train End":   str(train_px.index[-1].date()),
            "Test Start":  str(test_px.index[0].date()),
            "Test End":    str(test_px.index[-1].date()),
            "OOS Sharpe":  round(sharpe_oos, 3),
            "OOS Max DD":  round(mdd, 4),
            "n days":      len(net_ret),
        })

        cursor += n_test

    if not oos_chunks:
        return {"oos_returns": pd.Series(dtype=float), "fold_stats": [], "n_folds": 0}

    combined = pd.concat(oos_chunks).sort_index()
    return {
        "oos_returns": combined,
        "fold_stats":  fold_stats,
        "n_folds":     fold,
    }
