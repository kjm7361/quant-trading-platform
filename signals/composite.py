import pandas as pd

def rank_signal(signal: pd.DataFrame):
    """
    Cross-sectional rank by date.
    Higher signal = higher rank.
    """
    return signal.rank(axis=1, pct=True)


def composite_signal(momentum, value, profitability):
    """
    Equal-weighted Val-Mom-Prof signal
    """
    mom_rank = rank_signal(momentum)
    val_rank = rank_signal(value)
    prof_rank = rank_signal(profitability)

    composite = (mom_rank + val_rank + prof_rank) / 3
    return composite
