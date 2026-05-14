import pandas as pd

def generate_positions(signal: pd.DataFrame, long_q=0.7, short_q=0.3):
    """
    Generate long-short positions from composite signal
    """
    ranks = signal.rank(axis=1, pct=True)

    longs = (ranks >= long_q).astype(int)
    shorts = (ranks <= short_q).astype(int) * -1

    positions = longs + shorts

    # Normalize to dollar-neutral
    positions = positions.div(positions.abs().sum(axis=1), axis=0)

    return positions
