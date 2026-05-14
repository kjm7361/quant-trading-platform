import pandas as pd

def volatility_signal(price_df, window=60):
    returns = price_df.pct_change()
    vol = returns.rolling(window).std()
    return -vol  # lower vol = better
