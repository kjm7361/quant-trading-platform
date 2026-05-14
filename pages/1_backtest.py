import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

from components.layout import setup_page, section, next_step

from signals.momentum import momentum_signal
from signals.value import value_signal
from signals.profitability import profitability_signal

from portfolio.positions import generate_positions

from backtest.returns import compute_returns
from backtest.costs import apply_transaction_costs
from backtest.equity import compute_equity_curve
from backtest.metrics import sharpe_ratio, max_drawdown
from backtest.turnover import compute_turnover


# =============================
# Page setup
# =============================
setup_page(
    "Backtest",
    "Run the full factor strategy pipeline and evaluate performance after transaction costs.",
    "🧪"
)


# =============================
# Helper: composite signal
# =============================
def build_composite_signal(signal_list):
    ranked = [s.rank(axis=1, pct=True) for s in signal_list]
    combo = pd.concat(ranked, axis=0).groupby(level=0).mean()
    return combo


# =============================
# Intro
# =============================
st.info("This page runs your full backtest pipeline using selected factor signals, portfolio construction, transaction costs, and performance metrics.")

# =============================
# Sidebar controls
# =============================
st.sidebar.header("Strategy Controls")

use_momentum = st.sidebar.checkbox("Momentum", True)
use_value = st.sidebar.checkbox("Value", True)
use_profit = st.sidebar.checkbox("Profitability", True)

cost_bps = st.sidebar.slider("Transaction Cost (bps)", 0, 50, 10, step=5)
cost_rate = cost_bps / 10_000

st.sidebar.header("Data Source")
use_live = st.sidebar.checkbox("Use Live Market Data from Yahoo Finance")

# =============================
# Load data
# =============================
section("Data Loading", "Choose either live Yahoo Finance data or local project CSV data.")

if use_live:
    tickers = ["AAPL", "MSFT", "GOOG", "AMZN", "META"]

    raw = yf.download(
        tickers,
        start="2018-01-01",
        auto_adjust=False,
        progress=False
    )

    if raw is None or raw.empty:
        st.error("Could not download live market data.")
        st.stop()

    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw["Close"].to_frame()

    prices = prices.dropna()

    book = prices * 0.5
    mcap = prices * 10
    gprofit = prices * 0.3

    st.success("Live Yahoo Finance data loaded successfully.")
else:
    try:
        prices = pd.read_csv("data/prices.csv", parse_dates=["date"])
        prices = prices.pivot(index="date", columns="ticker", values="price")

        fund = pd.read_csv("data/fundamentals.csv", parse_dates=["date"])
        book = fund.pivot(index="date", columns="ticker", values="book_equity")
        mcap = fund.pivot(index="date", columns="ticker", values="market_cap")
        gprofit = fund.pivot(index="date", columns="ticker", values="gross_profit")

        st.success("Local CSV data loaded successfully.")
    except Exception as e:
        st.error(f"Could not load local CSV data: {e}")
        st.stop()

st.divider()

# =============================
# Build signals
# =============================
section("Signal Construction", "Combine selected factor signals into one composite ranking signal.")

signal_list = []

if use_momentum:
    signal_list.append(momentum_signal(prices))
if use_value:
    signal_list.append(value_signal(book, mcap))
if use_profit:
    signal_list.append(profitability_signal(gprofit, mcap))

if not signal_list:
    st.warning("Select at least one factor.")
    st.stop()

combo = build_composite_signal(signal_list)

selected_factors = []
if use_momentum:
    selected_factors.append("Momentum")
if use_value:
    selected_factors.append("Value")
if use_profit:
    selected_factors.append("Profitability")

st.write("Selected factors:", ", ".join(selected_factors))

st.divider()

# =============================
# Portfolio & backtest
# =============================
section("Portfolio Construction", "Generate positions, apply transaction costs, and compute net strategy returns.")

positions = generate_positions(combo).shift(1).fillna(0)

turnover = compute_turnover(positions)
avg_turnover = turnover.mean()

raw_returns = compute_returns(prices, positions)
costs = apply_transaction_costs(positions, cost_rate)
net_returns = raw_returns - costs

equity = compute_equity_curve(net_returns)

if len(equity) == 0:
    st.error("Equity curve could not be computed.")
    st.stop()

equity = equity / equity.iloc[0]

# Save for other pages
st.session_state["strategy_returns"] = net_returns.dropna()
st.session_state["equity_curve"] = equity.dropna()
st.session_state["initial_capital"] = 1.0

st.success("Backtest results saved for Risk Engine, Monte Carlo, Strategy DNA, and Dashboard.")

st.divider()

# =============================
# Metrics
# =============================
section("Performance Summary", "Core strategy metrics after transaction costs.")

sharpe = sharpe_ratio(net_returns)
mdd = max_drawdown(equity)

final_equity = float(equity.iloc[-1])
total_return = final_equity - 1

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Sharpe Ratio", f"{sharpe:.2f}")
c2.metric("Max Drawdown", f"{mdd:.2%}")
c3.metric("Final Equity", f"{final_equity:.2f}")
c4.metric("Total Return", f"{total_return:.2%}")
c5.metric("Avg Turnover", f"{avg_turnover:.2f}")

# =============================
# Performance insight
# =============================
section("Quick Insight")

if sharpe > 1 and mdd > -0.20:
    st.success("The strategy shows strong risk-adjusted performance with controlled drawdown.")
elif sharpe > 0:
    st.warning("The strategy has positive risk-adjusted performance, but risk or turnover should be reviewed.")
else:
    st.error("The strategy currently has weak risk-adjusted performance. Review signal quality, costs, and drawdown.")

st.divider()

# =============================
# Equity curve
# =============================
section("Equity Curve", "Growth of one dollar invested in the strategy after transaction costs.")

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(equity)
ax.set_title("Equity Curve Net of Costs")
ax.set_xlabel("Date")
ax.set_ylabel("Portfolio Value")
st.pyplot(fig)

# =============================
# Turnover
# =============================
section("Portfolio Turnover", "How much the portfolio changes over time.")

fig2, ax2 = plt.subplots(figsize=(10, 5))
ax2.plot(turnover)
ax2.set_title("Turnover Over Time")
ax2.set_xlabel("Date")
ax2.set_ylabel("Turnover")
st.pyplot(fig2)

st.divider()

# =============================
# Data previews
# =============================
section("Backtest Data Preview", "Recent net returns and portfolio weights.")

col1, col2 = st.columns(2)

with col1:
    st.write("Recent Net Returns")
    st.dataframe(net_returns.tail(10).to_frame("Net Return"), use_container_width=True)

with col2:
    st.write("Recent Positions")
    st.dataframe(positions.tail(10), use_container_width=True)

# =============================
# Next step
# =============================
next_step("Open Risk Engine or Monte Carlo next to analyze the saved backtest results in more detail.")