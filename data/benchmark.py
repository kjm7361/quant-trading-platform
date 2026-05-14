import pandas as pd
import yfinance as yf


def load_benchmark_prices(symbol="SPY", start="2018-01-01"):
    raw = yf.download(symbol, start=start, auto_adjust=True, progress=False)

    if "Close" in raw.columns:
        px = raw["Close"]
    else:
        px = raw.iloc[:, 0]

    px = px.dropna()
    px.name = symbol
    return px


def compute_benchmark_returns(benchmark_prices):
    return benchmark_prices.pct_change().fillna(0.0)
