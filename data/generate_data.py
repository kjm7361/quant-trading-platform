import pandas as pd
import numpy as np

# Reproducibility
np.random.seed(42)

# Create monthly dates
dates = pd.date_range("2015-01-31", "2020-12-31", freq="M")

# Fake tickers
tickers = ["AAPL", "MSFT", "GOOG", "AMZN", "META"]

# -------------------------
# Generate price data
# -------------------------
price_rows = []

for ticker in tickers:
    price = 100.0
    for date in dates:
        price *= 1 + np.random.normal(0.01, 0.05)  # drift + volatility
        price_rows.append([date, ticker, price])

prices = pd.DataFrame(price_rows, columns=["date", "ticker", "price"])
prices.to_csv("data/prices.csv", index=False)

# -------------------------
# Generate fundamentals
# -------------------------
fund_rows = []

for ticker in tickers:
    for date in dates:
        fund_rows.append([
            date,
            ticker,
            np.random.uniform(50, 150),    # book equity
            np.random.uniform(20, 80),     # gross profit
            np.random.uniform(200, 600)    # market cap
        ])

fundamentals = pd.DataFrame(
    fund_rows,
    columns=["date", "ticker", "book_equity", "gross_profit", "market_cap"]
)

fundamentals.to_csv("data/fundamentals.csv", index=False)

print("Synthetic price and fundamentals data generated.")
