import pandas as pd


def get_rebalance_dates(index, freq="M"):
    """
    Return a DatetimeIndex of rebalance dates based on a frequency.

    Parameters
    ----------
    index : DatetimeIndex
        Dates from your price/returns index.
    freq : str
        "D" = daily, "W" = weekly, "M" = monthly, "Q" = quarterly

    Notes
    -----
    We choose dates that exist in the provided index (trading days).
    For W/M/Q, we pick the last available date in each period.
    """
    idx = pd.DatetimeIndex(index)

    if freq == "D":
        return idx

    # Group by period and take the last available trading date in that period
    if freq == "W":
        periods = idx.to_period("W")
    elif freq == "M":
        periods = idx.to_period("M")
    elif freq == "Q":
        periods = idx.to_period("Q")
    else:
        # default monthly if unknown
        periods = idx.to_period("M")

    s = pd.Series(idx, index=idx)
    last_dates = s.groupby(periods).max().values
    return pd.DatetimeIndex(last_dates)


def apply_rebalance_rule(raw_positions, rebalance_dates):
    """
    Hold positions constant between rebalance dates.

    Parameters
    ----------
    raw_positions : DataFrame
        Index = dates, columns = tickers. These are the "desired" daily positions.
    rebalance_dates : DatetimeIndex
        Dates when portfolio is allowed to change.

    Returns
    -------
    DataFrame
        Positions that only update on rebalance dates and are forward-filled otherwise.
    """
    pos = raw_positions.copy()
    pos.index = pd.DatetimeIndex(pos.index)

    # Ensure rebalance_dates are aligned to pos index
    r = pd.DatetimeIndex(rebalance_dates)
    r = r[r.isin(pos.index)]

    # If no rebalance dates match, just return raw positions
    if len(r) == 0:
        return pos

    # Keep only rows on rebalance dates, then forward-fill
    pos_reb = pos.loc[r].copy()
    pos_reb = pos_reb.reindex(pos.index).ffill()

    # If the first dates are before the first rebalance date, fill with 0
    pos_reb = pos_reb.fillna(0.0)

    return pos_reb
