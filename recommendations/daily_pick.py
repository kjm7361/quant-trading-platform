import pandas as pd


def _safe_last(x):
    if x is None:
        return None
    if len(x) == 0:
        return None
    return x.iloc[-1]


def compute_daily_scores(close_prices: pd.DataFrame):
    """
    close_prices: DataFrame with Date index and tickers as columns (Close prices)
    Returns: (scores_df, diagnostics_df)
    """
    close_prices = close_prices.copy().dropna(how="all")

    # daily returns
    rets = close_prices.pct_change()

    # 3M momentum (about 63 trading days)
    mom_3m = close_prices.pct_change(63)

    # 12M momentum (about 252 trading days)
    mom_12m = close_prices.pct_change(252)

    # 3M volatility
    vol_3m = rets.rolling(63).std()

    # max drawdown over last 6M (~126 days)
    roll = close_prices.rolling(126)
    roll_max = roll.max()
    dd_6m = (close_prices / roll_max) - 1.0  # <= 0
    dd_6m_min = dd_6m.rolling(126).min()

    # last available row (today/most recent)
    mom3 = _safe_last(mom_3m)
    mom12 = _safe_last(mom_12m)
    vol3 = _safe_last(vol_3m)
    dd6 = _safe_last(dd_6m_min)

    diag = pd.DataFrame({
        "mom_3m": mom3,
        "mom_12m": mom12,
        "vol_3m": vol3,
        "worst_dd_6m": dd6
    })

    # scoring (simple & explainable)
    # higher momentum is good, lower vol is good, smaller drawdown is good
    # Convert to ranks so it works across different price scales
    mom_score = diag["mom_3m"].rank(pct=True) * 0.45 + diag["mom_12m"].rank(pct=True) * 0.35
    vol_score = (1.0 - diag["vol_3m"].rank(pct=True)) * 0.10
    dd_score = (1.0 - diag["worst_dd_6m"].rank(pct=True)) * 0.10

    total = mom_score + vol_score + dd_score

    scores = pd.DataFrame({
        "score": total
    }).sort_values("score", ascending=False)

    return scores, diag
