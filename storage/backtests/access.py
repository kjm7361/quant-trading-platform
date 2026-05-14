import pandas as pd
from pathlib import Path
from datetime import datetime

BASE = Path("storage/backtests")

def save_backtest(strategy_id, metrics, start, end):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    record = {
        "strategy_id": strategy_id,
        "start": start,
        "end": end,
        **metrics
    }

    path = BASE / f"{strategy_id}_{ts}.csv"
    pd.DataFrame([record]).to_csv(path, index=False)
