import numpy as np
import pandas as pd

def sharpe_ratio(returns: pd.Series, periods_per_year=12):
    """
    Annualized Sharpe ratio
    """
    mean = returns.mean() * periods_per_year
    std = returns.std() * np.sqrt(periods_per_year)
    return mean / std if std != 0 else 0


def max_drawdown(equity: pd.Series):
    """
    Maximum drawdown
    """
    rolling_max = equity.cummax()
    drawdown = equity / rolling_max - 1
    return drawdown.min()
