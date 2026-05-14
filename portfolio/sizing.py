import pandas as pd


def get_rebalance_dates(index, freq="M"):
    idx = pd.DatetimeIndex(index)

    if freq == "D":
        return idx

    if freq == "W":
        periods = idx.to_period("W")
    elif freq == "M":
        periods = idx.to_period("M")
    elif freq == "Q":
        periods = idx.to_period("Q")
    else:
        periods = idx.to_period("M")

    s = pd.Series(idx, index=idx)
    last_dates = s.groupby(periods).max().values
    return pd.DatetimeIndex(last_dates)


def apply_rebalance_rule(raw_positions, rebalance_dates):
    pos = raw_positions.copy()
    pos.index = pd.DatetimeIndex(pos.index)

    r = pd.DatetimeIndex(rebalance_dates)
    r = r[r.isin(pos.index)]

    if len(r) == 0:
        return pos

    pos_reb = pos.loc[r].copy()
    pos_reb = pos_reb.reindex(pos.index).ffill()
    pos_reb = pos_reb.fillna(0.0)

    return pos_reb
