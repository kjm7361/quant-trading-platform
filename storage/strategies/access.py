import pandas as pd
import uuid
from pathlib import Path

BASE = Path("storage/strategies/strategies.csv")

def create_strategy(name, signals, user_id):
    df = pd.read_csv(BASE)

    strategy_id = str(uuid.uuid4())

    df.loc[len(df)] = {
        "strategy_id": strategy_id,
        "name": name,
        "signals": ",".join(signals),
        "user_id": user_id
    }

    df.to_csv(BASE, index=False)
    return strategy_id


def list_strategies(user_id=None):
    df = pd.read_csv(BASE)
    if user_id:
        df = df[df["user_id"] == user_id]
    return df


def get_strategy(strategy_id):
    df = pd.read_csv(BASE)
    return df[df["strategy_id"] == strategy_id].iloc[0]
