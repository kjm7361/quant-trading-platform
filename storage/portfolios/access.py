import pandas as pd
from pathlib import Path

BASE = Path("storage/portfolios")

def save_portfolio(strategy_id, weights):
    path = BASE / f"{strategy_id}_portfolio.csv"
    weights.to_csv(path)
