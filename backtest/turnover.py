import pandas as pd

def compute_turnover(positions: pd.DataFrame) -> pd.Series:
    """
    Portfolio turnover = sum of absolute position changes.
    """
    trades = positions.diff().abs()
    turnover = trades.sum(axis=1)
    return turnover
