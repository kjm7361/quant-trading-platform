import pandas as pd


import pandas as pd

def returns_from_prices(prices):
    # If it's a DataFrame (e.g., shape (n,1)), take the first column
    if isinstance(prices, pd.DataFrame):
        if prices.shape[1] == 0:
            return pd.Series(dtype=float)
        prices = prices.iloc[:, 0]

    # If it's not already a Series, convert safely
    if not isinstance(prices, pd.Series):
        prices = pd.Series(prices)

    prices = prices.dropna()
    rets = prices.pct_change().dropna()
    return rets



def day_of_week_stats(rets: pd.Series) -> pd.DataFrame:
    """
    Mean/std return grouped by weekday.
    """
    r = pd.Series(rets).dropna()
    dow = r.index.dayofweek  # Mon=0 ... Fri=4
    out = r.groupby(dow).agg(["mean", "std"])
    out.index = ["Mon", "Tue", "Wed", "Thu", "Fri"][: len(out.index)]
    return out


def month_stats(rets: pd.Series) -> pd.DataFrame:
    """
    Mean/std return grouped by calendar month.
    """
    r = pd.Series(rets).dropna()
    m = r.index.month
    out = r.groupby(m).agg(["mean", "std"])
    out.index = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][: len(out.index)]
    return out


def turn_of_month_stats(rets: pd.Series, first_n_days: int = 3) -> pd.DataFrame:
    """
    Compare returns in first N trading days of each month vs the rest.
    """
    r = pd.Series(rets).dropna()

    # trading day number within each month: 1,2,3,...
    td_in_month = r.groupby([r.index.year, r.index.month]).cumcount() + 1

    tom = r[td_in_month <= first_n_days]
    rest = r[td_in_month > first_n_days]

    out = pd.DataFrame(
        {
            "mean": [tom.mean(), rest.mean()],
            "std": [tom.std(), rest.std()],
            "count": [tom.count(), rest.count()],
        },
        index=[f"Turn-of-month (first {first_n_days})", "Rest of month"],
    )
    return out


def reversal_vs_momentum(rets: pd.Series, lookback: int = 5, forward: int = 5) -> pd.DataFrame:
    """
    Bucket by past lookback-day return (quintiles) and compute next forward-day return stats.
    If high past-return buckets also have high forward returns -> momentum.
    If low past-return buckets rebound -> mean reversion.
    """
    r = pd.Series(rets).dropna()

    past = (1 + r).rolling(lookback).apply(lambda x: x.prod() - 1, raw=False)
    fut = (1 + r.shift(-1)).rolling(forward).apply(lambda x: x.prod() - 1, raw=False)

    df = pd.DataFrame({"past": past, "fut": fut}).dropna()

    # 5 buckets: Q1..Q5
    df["bucket"] = pd.qcut(df["past"], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])

    out = df.groupby("bucket")["fut"].agg(["mean", "std", "count"])
    return out
