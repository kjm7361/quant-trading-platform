"""
backtest/ic.py
Information Coefficient analysis — the standard factor research metric.

IC = Spearman rank correlation between signal_t and forward_return_{t+h}.
A good factor should have mean IC > 0.02 and ICIR > 0.5.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def information_coefficient(
    signal: pd.DataFrame,
    price_returns: pd.DataFrame,
    horizon: int = 1,
) -> pd.Series:
    """
    Per-date cross-sectional IC (Spearman rank correlation).

    Parameters
    ----------
    signal : pd.DataFrame
        Cross-sectional factor scores (date × ticker).
    price_returns : pd.DataFrame
        Daily simple returns (date × ticker).
    horizon : int
        Forward-return window in days.

    Returns
    -------
    pd.Series
        IC value per date.
    """
    fwd = price_returns.shift(-horizon)
    dates = signal.index.intersection(fwd.index)

    ics: list[float] = []
    for d in dates:
        s = signal.loc[d].dropna()
        r = fwd.loc[d].dropna()
        common = s.index.intersection(r.index)
        if len(common) < 5:
            ics.append(np.nan)
            continue
        ic = float(s[common].rank().corr(r[common].rank()))
        ics.append(ic)

    return pd.Series(ics, index=dates, name="IC")


def icir(ic_series: pd.Series) -> float:
    """
    IC Information Ratio = mean(IC) / std(IC).
    Higher is better; > 0.5 is considered strong.
    """
    ic = ic_series.dropna()
    if len(ic) < 2:
        return 0.0
    std = ic.std()
    return float(ic.mean() / std) if std > 0 else 0.0


def ic_decay(
    signal: pd.DataFrame,
    price_returns: pd.DataFrame,
    max_horizon: int = 20,
) -> pd.Series:
    """
    Mean IC at each forward horizon from 1 to max_horizon days.
    A good signal decays slowly — still positive IC at horizon 5-10.

    Returns
    -------
    pd.Series
        Index = horizon (days), values = mean IC.
    """
    results: dict[int, float] = {}
    for h in range(1, max_horizon + 1):
        ic = information_coefficient(signal, price_returns, horizon=h)
        results[h] = float(ic.mean())
    return pd.Series(results, name="Mean IC")


def rolling_icir(
    signal: pd.DataFrame,
    price_returns: pd.DataFrame,
    horizon: int = 1,
    window: int = 63,
) -> pd.Series:
    """
    Rolling ICIR over a trailing window of dates.
    Useful for detecting when a factor's predictive power degrades.
    """
    ic = information_coefficient(signal, price_returns, horizon=horizon)
    roll_mean = ic.rolling(window).mean()
    roll_std  = ic.rolling(window).std()
    return (roll_mean / roll_std.replace(0, np.nan)).rename("Rolling ICIR")


def ic_summary(
    signal: pd.DataFrame,
    price_returns: pd.DataFrame,
    horizons: list[int] | None = None,
) -> pd.DataFrame:
    """
    Summary table: mean IC, std IC, ICIR, t-stat at each horizon.
    """
    if horizons is None:
        horizons = [1, 3, 5, 10, 20]

    rows = []
    for h in horizons:
        ic = information_coefficient(signal, price_returns, horizon=h)
        mean = float(ic.mean())
        std  = float(ic.std())
        n    = int(ic.dropna().shape[0])
        t    = float(mean / (std / np.sqrt(n))) if std > 0 and n > 0 else 0.0
        rows.append({
            "Horizon (days)": h,
            "Mean IC":        round(mean, 4),
            "Std IC":         round(std, 4),
            "ICIR":           round(mean / std, 3) if std > 0 else 0.0,
            "t-stat":         round(t, 2),
            "n":              n,
        })

    return pd.DataFrame(rows).set_index("Horizon (days)")
