import pandas as pd

def momentum_signal(prices: pd.DataFrame):
    """
    12-1 momentum:
    product of returns from t-12 to t-2
    """
    returns = prices.pct_change()
    momentum = (1 + returns).rolling(12).apply(
        lambda x: x[:-1].prod() - 1,
        raw=False
    )
    return momentum
