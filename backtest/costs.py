import pandas as pd

def apply_transaction_costs(positions: pd.DataFrame, cost_rate=0.001):
    """
    Compute transaction costs based on portfolio turnover
    """
    # Change in positions (turnover)
    turnover = positions.diff().abs().sum(axis=1)

    # Cost = turnover * cost rate
    costs = turnover * cost_rate

    return costs
