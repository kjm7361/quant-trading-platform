import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

from components.layout import setup_page, section, next_step

from market.anomalies import (
    returns_from_prices,
    day_of_week_stats,
    month_stats,
    turn_of_month_stats,
    reversal_vs_momentum
)


# =============================
# Page setup
# =============================
setup_page(
    "Market Anomalies",
    "Explore repeatable market patterns such as seasonality, day-of-week effects, turn-of-month behavior, and momentum versus reversal.",
    "🧠"
)


# -------------------------
# Controls
# -------------------------
st.sidebar.header("Anomaly Controls")

symbol = st.sidebar.selectbox("Market Proxy", ["SPY", "QQQ", "IWM", "DIA"], index=0)
start = st.sidebar.date_input("Start Date", value=pd.to_datetime("2015-01-01"))
use_adjusted = st.sidebar.checkbox("Use Adjusted Close", True)

first_n = st.sidebar.slider("Turn-of-month: first N trading days", 1, 7, 3)
lookback = st.sidebar.slider("Reversal/Momentum lookback days", 2, 20, 5)
forward = st.sidebar.slider("Forward window days", 2, 20, 5)

# -------------------------
# Data
# -------------------------
section("Market Data", "Download historical market data and compute returns for anomaly analysis.")

raw = yf.download(symbol, start=str(start), progress=False)

if raw.empty:
    st.error("No data returned. Try a different symbol or start date.")
    st.stop()

price_col = "Adj Close" if use_adjusted and "Adj Close" in raw.columns else "Close"
prices = raw[price_col].dropna()
rets = returns_from_prices(prices)

if len(rets) == 0:
    st.error("Not enough return data to run anomaly analysis.")
    st.stop()

last_date = prices.index.max().date()
total_return = float((prices.iloc[-1] / prices.iloc[0]) - 1)
avg_daily_return = float(rets.mean())
daily_vol = float(rets.std())

m1, m2, m3, m4 = st.columns(4)
m1.metric("Symbol", symbol)
m2.metric("Last Date", str(last_date))
m3.metric("Total Return", f"{total_return:.2%}")
m4.metric("Daily Volatility", f"{daily_vol:.4%}")

st.caption(f"Using {price_col} prices from Yahoo Finance.")

st.divider()

# -------------------------
# 1) Day-of-week effect
# -------------------------
section("Day-of-Week Effect", "Average return behavior by weekday.")

dow = day_of_week_stats(rets)

c1, c2 = st.columns([1, 2])
with c1:
    st.dataframe(dow.style.format({"mean": "{:.4%}", "std": "{:.4%}"}), use_container_width=True)

with c2:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(dow.index, dow["mean"])
    ax.set_title("Average Daily Return by Weekday")
    ax.set_ylabel("Mean Daily Return")
    ax.set_xlabel("Weekday")
    st.pyplot(fig)

if dow["mean"].max() > 0:
    best_day = str(dow["mean"].idxmax())
    st.success(f"Best average weekday effect in this sample: {best_day}")
else:
    st.warning("No weekday has a positive average return in this sample.")

st.divider()

# -------------------------
# 2) Month seasonality
# -------------------------
section("Month / Seasonality", "Average return behavior across calendar months.")

mon = month_stats(rets)

c1, c2 = st.columns([1, 2])
with c1:
    st.dataframe(mon.style.format({"mean": "{:.4%}", "std": "{:.4%}"}), use_container_width=True)

with c2:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(mon.index, mon["mean"])
    ax.set_title("Average Daily Return by Month")
    ax.set_ylabel("Mean Daily Return")
    ax.set_xlabel("Month")
    st.pyplot(fig)

best_month = str(mon["mean"].idxmax())
worst_month = str(mon["mean"].idxmin())
st.info(f"Best average month in this sample: {best_month}. Weakest average month: {worst_month}.")

st.divider()

# -------------------------
# 3) Turn-of-month
# -------------------------
section("Turn-of-the-Month", "Compare early-month trading days against the rest of the month.")

tom = turn_of_month_stats(rets, first_n_days=first_n)

c1, c2 = st.columns([1, 2])
with c1:
    st.dataframe(tom.style.format({"mean": "{:.4%}", "std": "{:.4%}"}), use_container_width=True)

with c2:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(tom.index, tom["mean"])
    ax.set_title("Average Daily Return: Turn-of-Month vs Rest")
    ax.set_ylabel("Mean Daily Return")
    ax.set_xlabel("Bucket")
    st.pyplot(fig)

if len(tom) >= 2:
    best_bucket = str(tom["mean"].idxmax())
    st.info(f"Stronger average bucket in this sample: {best_bucket}")

st.divider()

# -------------------------
# 4) Momentum vs Reversal
# -------------------------
section("Momentum vs Mean Reversion", "Compare future returns after strong versus weak recent performance.")

mr = reversal_vs_momentum(rets, lookback=lookback, forward=forward)

c1, c2 = st.columns([1, 2])
with c1:
    st.dataframe(mr.style.format({"mean": "{:.4%}", "std": "{:.4%}"}), use_container_width=True)

with c2:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(mr.index, mr["mean"])
    ax.set_title(f"Next {forward}-day Return After Past {lookback}-day Move")
    ax.set_ylabel("Mean Forward Return")
    ax.set_xlabel("Past-Return Bucket")
    st.pyplot(fig)

# -------------------------
# Interpretation
# -------------------------
section("Interpretation")

try:
    q1 = float(mr.loc["Q1", "mean"])
    q5 = float(mr.loc["Q5", "mean"])

    if q5 > q1:
        st.success("Q5 has higher future returns than Q1. This suggests momentum behavior in this sample.")
    elif q1 > q5:
        st.warning("Q1 rebounds more than Q5. This suggests mean reversion behavior in this sample.")
    else:
        st.info("Q1 and Q5 are similar. No clear momentum or reversal pattern appears.")
except:
    st.info(
        "If Q5 has higher future returns than Q1, that suggests momentum. "
        "If Q1 rebounds more than Q5, that suggests mean reversion."
    )

next_step("Use Daily Picks or Backtest next to test whether these anomaly patterns can become tradable signals.")