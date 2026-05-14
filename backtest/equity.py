import pandas as pd

def compute_equity_curve(returns: pd.Series):
    """
    Compute cumulative equity curve from returns
    """
    equity = (1 + returns.fillna(0)).cumprod()
    return equity
