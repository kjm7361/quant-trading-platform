import pandas as pd

def compute_returns(prices: pd.DataFrame, positions: pd.DataFrame):
    """
    Compute portfolio returns given prices and positions
    """
    # Asset returns
    asset_returns = prices.pct_change().shift(-1)

    # Align positions and returns
    aligned_pos = positions.loc[asset_returns.index]

    # Portfolio return
    portfolio_returns = (aligned_pos * asset_returns).sum(axis=1)

    return portfolio_returns
