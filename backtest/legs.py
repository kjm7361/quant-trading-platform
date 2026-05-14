import pandas as pd


def split_long_short(positions):
    """
    Split positions into long-only and short-only weights.

    positions: DataFrame (date x ticker)
    Returns: (long_w, short_w) DataFrames
      - long_w >= 0
      - short_w <= 0
    """
    w = positions.copy()
    long_w = w.clip(lower=0.0)
    short_w = w.clip(upper=0.0)
    return long_w, short_w


def leg_returns(prices, positions):
    """
    Compute daily returns for long leg, short leg, and long-short spread.

    prices: DataFrame (date x ticker) prices
    positions: DataFrame (date x ticker) weights/positions aligned to prices

    Returns: (long_ret, short_ret, spread_ret) as Series
    """
    px = prices.copy()
    w = positions.copy()

    # Align indices/columns
    common_idx = px.index.intersection(w.index)
    common_cols = px.columns.intersection(w.columns)

    px = px.loc[common_idx, common_cols]
    w = w.loc[common_idx, common_cols]

    asset_ret = px.pct_change().fillna(0.0)

    long_w, short_w = split_long_short(w)

    # Normalize within each leg to avoid scale issues
    long_sum = long_w.abs().sum(axis=1).replace(0.0, 1.0)
    short_sum = short_w.abs().sum(axis=1).replace(0.0, 1.0)

    long_norm = long_w.div(long_sum, axis=0)
    short_norm = short_w.div(short_sum, axis=0)

    long_ret = (long_norm * asset_ret).sum(axis=1)
    short_ret = (short_norm * asset_ret).sum(axis=1)

    spread_ret = long_ret - short_ret

    return long_ret, short_ret, spread_ret
