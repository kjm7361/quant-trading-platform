import pandas as pd
import numpy as np


def annualize_mean(daily_returns, periods_per_year=252):
    r = pd.Series(daily_returns).dropna()
    if len(r) == 0:
        return 0.0
    return float(r.mean() * periods_per_year)


def annualize_vol(daily_returns, periods_per_year=252):
    r = pd.Series(daily_returns).dropna()
    if len(r) == 0:
        return 0.0
    return float(r.std() * (periods_per_year ** 0.5))


def sharpe(daily_returns, periods_per_year=252):
    r = pd.Series(daily_returns).dropna()
    if len(r) == 0:
        return 0.0
    vol = r.std()
    if vol == 0 or np.isnan(vol):
        return 0.0
    return float((r.mean() / vol) * (periods_per_year ** 0.5))


def t_stat(daily_returns):
    """
    Classic t-stat of mean daily return (assumes iid).
    """
    r = pd.Series(daily_returns).dropna()
    if len(r) < 2:
        return 0.0
    s = r.std()
    if s == 0 or np.isnan(s):
        return 0.0
    return float(r.mean() / (s / (len(r) ** 0.5)))


def summary_table(long_ret, short_ret, spread_ret):
    """
    Returns a DataFrame with annualized stats + t-stat for spread.
    """
    data = {
        "Long": long_ret,
        "Short": short_ret,
        "Long-Short": spread_ret
    }

    rows = []
    for name, series in data.items():
        rows.append({
            "Leg": name,
            "Ann Return": annualize_mean(series),
            "Ann Vol": annualize_vol(series),
            "Sharpe": sharpe(series),
            "t-stat": t_stat(series) if name == "Long-Short" else np.nan
        })

    df = pd.DataFrame(rows).set_index("Leg")
    return df
