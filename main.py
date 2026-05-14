import pandas as pd
import matplotlib.pyplot as plt

from signals.momentum import momentum_signal
from signals.value import value_signal
from signals.profitability import profitability_signal
from signals.composite import composite_signal
from portfolio.positions import generate_positions
from backtest.returns import compute_returns
from backtest.costs import apply_transaction_costs
from backtest.equity import compute_equity_curve
from backtest.metrics import sharpe_ratio, max_drawdown

# -----------------------------
# Load price data
# -----------------------------
prices = pd.read_csv("data/prices.csv", parse_dates=["date"])
prices = prices.pivot(index="date", columns="ticker", values="price")

# -----------------------------
# Load fundamentals
# -----------------------------
fund = pd.read_csv("data/fundamentals.csv", parse_dates=["date"])

book = fund.pivot(index="date", columns="ticker", values="book_equity")
mcap = fund.pivot(index="date", columns="ticker", values="market_cap")
profit = fund.pivot(index="date", columns="ticker", values="gross_profit")

# -----------------------------
# Signals
# -----------------------------
mom = momentum_signal(prices)
val = value_signal(book, mcap)
prof = profitability_signal(profit, mcap)

combo = composite_signal(mom, val, prof)

# -----------------------------
# Positions
# -----------------------------
positions = generate_positions(combo)

# -----------------------------
# Returns & costs
# -----------------------------
raw_returns = compute_returns(prices, positions)
costs = apply_transaction_costs(positions)
net_returns = raw_returns - costs

# -----------------------------
# Equity curve
# -----------------------------
equity = compute_equity_curve(net_returns)

# -----------------------------
# Metrics
# -----------------------------
sharpe = sharpe_ratio(net_returns)
mdd = max_drawdown(equity)

print(f"Final equity value: {equity.iloc[-1]:.2f}")
print(f"Sharpe ratio: {sharpe:.2f}")
print(f"Max drawdown: {mdd:.2%}")

# -----------------------------
# Plot
# -----------------------------
plt.figure()
plt.plot(equity)
plt.title("Equity Curve — Val-Mom-Prof Strategy")
plt.xlabel("Date")
plt.ylabel("Portfolio Value")
plt.show()
