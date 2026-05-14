import pandas as pd


import pandas as pd


import pandas as pd
import numpy as np


def _to_1d(x):
    # pandas DataFrame -> Series
    if isinstance(x, pd.DataFrame):
        if x.shape[1] == 1:
            return x.iloc[:, 0]
        return x.iloc[:, 0]

    # pandas Series -> Series
    if isinstance(x, pd.Series):
        return x

    # numpy arrays -> flatten safely
    if isinstance(x, np.ndarray):
        if x.ndim == 2 and x.shape[1] == 1:
            return pd.Series(x[:, 0])
        if x.ndim == 2 and x.shape[0] == 1:
            return pd.Series(x[0, :])
        if x.ndim >= 2:
            return pd.Series(x.reshape(-1))
        return pd.Series(x)

    # python lists (including list-of-lists) -> flatten if needed
    if isinstance(x, list):
        arr = np.array(x)
        if arr.ndim >= 2:
            arr = arr.reshape(-1)
        return pd.Series(arr)

    # fallback
    return pd.Series(x)


def align_series(a, b):
    a = _to_1d(a).copy()
    b = _to_1d(b).copy()

    df = pd.concat([a, b], axis=1).dropna()
    return df.iloc[:, 0], df.iloc[:, 1]



def alpha_beta(strategy_returns, benchmark_returns, periods_per_year=252):
    rs, rb = align_series(strategy_returns, benchmark_returns)

    var_b = rb.var()
    if var_b == 0 or pd.isna(var_b):
        return 0.0, 0.0

    beta = rb.cov(rs) / var_b
    alpha_daily = rs.mean() - beta * rb.mean()
    alpha_annual = alpha_daily * periods_per_year
    return float(alpha_annual), float(beta)


def tracking_error(strategy_returns, benchmark_returns, periods_per_year=252):
    rs, rb = align_series(strategy_returns, benchmark_returns)
    diff = rs - rb
    te = diff.std() * (periods_per_year ** 0.5)
    return float(te)


def information_ratio(strategy_returns, benchmark_returns, periods_per_year=252):
    rs, rb = align_series(strategy_returns, benchmark_returns)
    excess = rs - rb

    denom = excess.std()
    if denom == 0 or pd.isna(denom):
        return 0.0

    ir = (excess.mean() / denom) * (periods_per_year ** 0.5)
    return float(ir)


def equity_from_returns(returns):
    # Handle Series / DataFrame / numpy (n,1) safely
    if isinstance(returns, pd.DataFrame):
        if returns.shape[1] == 1:
            returns = returns.iloc[:, 0]
        else:
            returns = returns.iloc[:, 0]

    r = returns

    # If still not a Series, convert carefully
    if not isinstance(r, pd.Series):
        try:
            # numpy (n,1) -> flatten
            import numpy as np
            if isinstance(r, np.ndarray) and r.ndim == 2 and r.shape[1] == 1:
                r = r[:, 0]
            elif isinstance(r, np.ndarray) and r.ndim >= 2:
                r = r.reshape(-1)
        except Exception:
            pass

        r = pd.Series(r)

    r = r.fillna(0.0)

    eq = (1.0 + r).cumprod()
    if len(eq) == 0:
        return eq
    return eq / eq.iloc[0]
