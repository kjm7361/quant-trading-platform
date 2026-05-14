from backtest.legs import leg_returns
from backtest.anomaly_stats import summary_table

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from reports.report import build_html_report


from signals.momentum import momentum_signal
from signals.value import value_signal
from signals.profitability import profitability_signal

from portfolio.positions import generate_positions
from portfolio.rebalance import get_rebalance_dates, apply_rebalance_rule  

from backtest.returns import compute_returns
from backtest.costs import apply_transaction_costs
from backtest.equity import compute_equity_curve
from backtest.metrics import sharpe_ratio, max_drawdown
from backtest.turnover import compute_turnover

from stratergy_store import save_strategy, load_strategies, get_user_strategies
from auth import authenticate, save_user
from data.benchmark import load_benchmark_prices, compute_benchmark_returns
from backtest.benchmark import alpha_beta, information_ratio, tracking_error, equity_from_returns
from reports.pdf import build_pdf_report
from portfolio.blotter import holdings_snapshot, trade_blotter
from utils.exports import df_to_csv_bytes, series_to_csv_bytes







# =============================
# Helper: composite signal
# =============================
def build_composite_signal(signal_list):
    ranked = [s.rank(axis=1, pct=True) for s in signal_list]
    combo = pd.concat(ranked, axis=0).groupby(level=0).mean()
    return combo


# =============================
# Streamlit setup
# =============================
st.set_page_config(page_title="Quant Research Platform", layout="wide")


# =============================
# Authentication
# =============================
st.sidebar.header("👤 Account")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

if not st.session_state.logged_in:
    tab1, tab2 = st.sidebar.tabs(["Login", "Register"])

    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if authenticate(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid username or password")

    with tab2:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")

        if st.button("Register"):
            if save_user(new_user, new_pass):
                st.success("Account created! Please log in.")
            else:
                st.error("Username already exists")

    st.stop()


# =============================
# Logout (NEW)
# =============================
st.sidebar.success(f"Logged in as: {st.session_state.username}")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()


# =============================
# App header
# =============================
st.title("📊 Cost-Aware Quant Research Platform")
st.markdown(
    """
This app simulates **long–short factor portfolios** under realistic transaction costs.

⚠️ **Not a predictor**  
✅ **Institutional-style research & portfolio simulation engine**
"""
)


# =============================
# Sidebar controls
# =============================
st.sidebar.header("⚙️ Strategy Controls")

use_momentum = st.sidebar.checkbox("Momentum", True)
use_value = st.sidebar.checkbox("Value", True)
use_profit = st.sidebar.checkbox("Profitability", True)

cost_bps = st.sidebar.slider("Transaction Cost (bps)", 0, 50, 10, step=5)
cost_rate = cost_bps / 10_000

# ✅ ADDED (rebalance control) — does not change anything else
st.sidebar.header("📅 Rebalance")
rebalance_freq = st.sidebar.selectbox(
    "Rebalance Frequency",
    ["D", "W", "M", "Q"],
    index=2
)

st.sidebar.header("🌍 Data Source")
use_live = st.sidebar.checkbox("Use Live Market Data (Yahoo Finance)")


# =============================
# Load data
# =============================
if use_live:
    tickers = ["AAPL", "MSFT", "GOOG", "AMZN", "META"]

    raw = yf.download(
        tickers,
        start="2018-01-01",
        auto_adjust=False,
        progress=False
    )

    # ✅ FIX: extract Close prices safely
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw["Close"].to_frame()

    prices = prices.dropna()

    # Dummy fundamentals (structure-compatible)
    book = prices * 0.5
    mcap = prices * 10
    gprofit = prices * 0.3

else:
    prices = pd.read_csv("data/prices.csv", parse_dates=["date"])
    prices = prices.pivot(index="date", columns="ticker", values="price")

    fund = pd.read_csv("data/fundamentals.csv", parse_dates=["date"])
    book = fund.pivot(index="date", columns="ticker", values="book_equity")
    mcap = fund.pivot(index="date", columns="ticker", values="market_cap")
    gprofit = fund.pivot(index="date", columns="ticker", values="gross_profit")


# =============================
# Build signals
# =============================
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


# =============================
# Portfolio & backtest
# =============================
# KEEP YOUR LOGIC SAME, just insert rebalance layer
raw_positions = generate_positions(combo).shift(1).fillna(0)  # ✅ same as your original positions line

reb_dates = get_rebalance_dates(raw_positions.index, freq=rebalance_freq)  # ✅ ADDED
positions = apply_rebalance_rule(raw_positions, reb_dates)                 # ✅ ADDED

turnover = compute_turnover(positions)
avg_turnover = turnover.mean()

raw_returns = compute_returns(prices, positions)
costs = apply_transaction_costs(positions, cost_rate)
net_returns = raw_returns - costs

equity = compute_equity_curve(net_returns)
equity = equity / equity.iloc[0]


# =============================
# Metrics
# =============================
sharpe = sharpe_ratio(net_returns)
mdd = max_drawdown(equity)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Sharpe Ratio", f"{sharpe:.2f}")
c2.metric("Max Drawdown", f"{mdd:.2%}")
c3.metric("Final Equity", f"{equity.iloc[-1]:.2f}")
c4.metric("Avg Turnover", f"{avg_turnover:.2f}")


# =============================
# Save strategy
# =============================
st.sidebar.header("💾 Save Strategy")

if st.sidebar.button("Save Strategy"):
    factors = []

    if use_momentum:
        factors.append("Momentum")
    if use_value:
        factors.append("Value")
    if use_profit:
        factors.append("Profitability")

    payload = {
        "signals": factors,
        "user_id": st.session_state["username"],

        # optional metadata (safe defaults)
        "metrics": {
            "sharpe": float(sharpe),
            "max_drawdown": float(mdd),
            "final_equity": float(equity.iloc[-1]),
            "avg_turnover": float(avg_turnover),
            "cost_bps": int(cost_bps),
        },
        "start": str(prices.index.min().date()) if len(prices.index) > 0 else "unknown",
        "end": str(prices.index.max().date()) if len(prices.index) > 0 else "unknown",
    }

    # name can be whatever you want shown in storage
    strategy_name = f"{st.session_state['username']}_strategy"

    save_strategy(strategy_name, payload)

    st.sidebar.success("Strategy saved!")


# =============================
# Equity curve
# =============================
st.header("📈 Equity Curve")

fig, ax = plt.subplots()
ax.plot(equity)
ax.set_title("Equity Curve (Net of Costs)")
ax.set_xlabel("Date")
ax.set_ylabel("Portfolio Value")
st.pyplot(fig)


# =============================
# Turnover
# =============================
st.header("🔁 Portfolio Turnover")

fig2, ax2 = plt.subplots()
ax2.plot(turnover)
ax2.set_title("Turnover Over Time")
ax2.set_xlabel("Date")
ax2.set_ylabel("Turnover")
st.pyplot(fig2)


# =============================
# Holdings + Trade Blotter (NEW FEATURE)  ✅✅ ADDED HERE
# =============================
st.header("🧾 Holdings & Trade Blotter")

st.subheader("📌 Current Holdings Snapshot")

top_n = st.slider("Top N holdings to display", min_value=5, max_value=25, value=10, step=5)

long_df, short_df = holdings_snapshot(positions, asof=None, top_n=top_n)

cL, cS = st.columns(2)

with cL:
    st.write("✅ Top Longs")
    if long_df.empty:
        st.info("No long holdings on this date.")
    else:
        st.dataframe(long_df.style.format({"Weight": "{:.4f}"}), use_container_width=True)

with cS:
    st.write("🔻 Top Shorts")
    if short_df.empty:
        st.info("No short holdings on this date.")
    else:
        st.dataframe(short_df.style.format({"Weight": "{:.4f}"}), use_container_width=True)

st.subheader("🔁 Trade Blotter (Rebalance Trades)")

threshold = st.number_input(
    "Ignore trades smaller than (abs weight change)",
    min_value=0.0,
    max_value=0.05,
    value=0.001,
    step=0.001,
    format="%.3f"
)

blotter_df = trade_blotter(positions, reb_dates, threshold=threshold)

if blotter_df.empty:
    st.info("No trades found (try lowering the threshold or changing rebalance frequency).")
else:
    st.caption("Trade = NewWeight − PrevWeight (positive = buy more / cover short, negative = sell / short more)")
    st.dataframe(
        blotter_df.style.format({
            "PrevWeight": "{:.4f}",
            "NewWeight": "{:.4f}",
            "Trade": "{:.4f}",
        }),
        use_container_width=True
    )


# =============================
# Saved strategies
# =============================
st.header("📁 My Saved Strategies")

saved = load_strategies()

if not saved.empty:
    st.dataframe(saved)
else:
    st.info("No saved strategies yet.")


# =============================
# Risk Dashboard
# =============================
st.header("⚠️ Risk Dashboard")

st.subheader("📉 Rolling Risk Metrics")

rolling_window = st.slider(
    "Rolling Window (months)",
    min_value=6,
    max_value=36,
    value=12,
    step=3
)

rolling_vol = net_returns.rolling(rolling_window).std()
rolling_sharpe = (
    net_returns.rolling(rolling_window).mean() /
    net_returns.rolling(rolling_window).std()
) * (12 ** 0.5)

fig_vol, ax_vol = plt.subplots()
ax_vol.plot(rolling_vol)
ax_vol.set_title(f"{rolling_window}-Month Rolling Volatility")
ax_vol.set_xlabel("Date")
ax_vol.set_ylabel("Volatility")
st.pyplot(fig_vol)

fig_sharpe, ax_sharpe = plt.subplots()
ax_sharpe.plot(rolling_sharpe)
ax_sharpe.set_title(f"{rolling_window}-Month Rolling Sharpe Ratio")
ax_sharpe.set_xlabel("Date")
ax_sharpe.set_ylabel("Sharpe")
st.pyplot(fig_sharpe)

st.subheader("📉 Drawdown Analysis")

drawdown = equity / equity.cummax() - 1

fig_dd, ax_dd = plt.subplots()
ax_dd.plot(drawdown, color="red")
ax_dd.set_title("Drawdown Over Time")
ax_dd.set_xlabel("Date")
ax_dd.set_ylabel("Drawdown")
st.pyplot(fig_dd)

st.subheader("📆 Worst Monthly Returns")

monthly_returns = net_returns.resample("M").sum()
worst_months = monthly_returns.nsmallest(5)

st.dataframe(
    worst_months.rename("Monthly Return")
)


# =============================
# Parameter Sensitivity Analysis
# =============================
st.header("🧪 Parameter Sensitivity (Robustness Test)")

st.subheader("🔧 Stress Test Parameters")

cost_range = st.multiselect(
    "Transaction Cost Scenarios (bps)",
    options=[0, 5, 10, 15, 20, 30, 40, 50],
    default=[0, 10, 20, 30]
)

rebalance_lag = st.slider(
    "Rebalance Lag (months)",
    min_value=1,
    max_value=6,
    value=1
)

results = []

for cost in cost_range:
    cost_rate_test = cost / 10_000

    # Apply rebalance lag
    pos_test = positions.shift(rebalance_lag).fillna(0)

    ret_test = compute_returns(prices, pos_test)
    cost_test = apply_transaction_costs(pos_test, cost_rate_test)
    net_test = ret_test - cost_test

    equity_test = compute_equity_curve(net_test)
    equity_test = equity_test / equity_test.iloc[0]

    results.append({
        "Cost (bps)": cost,
        "Sharpe": sharpe_ratio(net_test),
        "Max Drawdown": max_drawdown(equity_test),
        "Final Equity": equity_test.iloc[-1]
    })

sens_df = pd.DataFrame(results)

st.subheader("📊 Sensitivity Results")
st.dataframe(
    sens_df.style.format({
        "Sharpe": "{:.2f}",
        "Max Drawdown": "{:.2%}",
        "Final Equity": "{:.2f}"
    })
)

st.subheader("📈 Performance vs Transaction Costs")

fig_sens, ax_sens = plt.subplots()
ax_sens.plot(sens_df["Cost (bps)"], sens_df["Sharpe"], marker="o")
ax_sens.set_xlabel("Transaction Cost (bps)")
ax_sens.set_ylabel("Sharpe Ratio")
ax_sens.set_title("Sharpe Sensitivity to Transaction Costs")
st.pyplot(fig_sens)


# =============================
# Strategy Comparison Playground
# =============================
st.header("📊 Strategy Comparison Playground")

strategies = {
    "Momentum": [momentum_signal(prices)],
    "Value": [value_signal(book, mcap)],
    "Profitability": [profitability_signal(gprofit, mcap)],
    "Composite": signal_list
}

comparison_results = {}
equity_curves = {}

for name, sigs in strategies.items():
    combo_tmp = build_composite_signal(sigs)

    # ✅ keep your logic same, add rebalance layer here too
    raw_pos_tmp = generate_positions(combo_tmp).shift(1).fillna(0)
    reb_dates_tmp = get_rebalance_dates(raw_pos_tmp.index, freq=rebalance_freq)
    pos_tmp = apply_rebalance_rule(raw_pos_tmp, reb_dates_tmp)

    ret_tmp = compute_returns(prices, pos_tmp)
    cost_tmp = apply_transaction_costs(pos_tmp, cost_rate)
    net_tmp = ret_tmp - cost_tmp

    eq_tmp = compute_equity_curve(net_tmp)
    eq_tmp = eq_tmp / eq_tmp.iloc[0]

    comparison_results[name] = {
        "Sharpe": sharpe_ratio(net_tmp),
        "Max Drawdown": max_drawdown(eq_tmp),
        "Final Equity": eq_tmp.iloc[-1]
    }

    equity_curves[name] = eq_tmp

st.subheader("📋 Strategy Metrics Comparison")

comp_df = pd.DataFrame(comparison_results).T

st.dataframe(
    comp_df.style.format({
        "Sharpe": "{:.2f}",
        "Max Drawdown": "{:.2%}",
        "Final Equity": "{:.2f}"
    })
)

st.subheader("📈 Equity Curve Comparison")

selected = st.multiselect(
    "Select strategies to compare",
    options=list(equity_curves.keys()),
    default=["Composite"]
)

fig_cmp, ax_cmp = plt.subplots()

for name in selected:
    ax_cmp.plot(equity_curves[name], label=name)

ax_cmp.set_title("Equity Curve Comparison")
ax_cmp.set_xlabel("Date")
ax_cmp.set_ylabel("Normalized Equity")
ax_cmp.legend()

st.pyplot(fig_cmp)


# =============================
# Benchmark Dashboard (NEW FEATURE)
# =============================
st.header("📌 Benchmark Dashboard (SPY / QQQ)")

bench_symbol = st.selectbox("Benchmark", ["SPY", "QQQ", "IWM", "DIA"], index=0)

start_date = "2018-01-01"
if len(prices.index) > 0:
    start_date = str(prices.index.min().date())

bench_prices = load_benchmark_prices(symbol=bench_symbol, start=start_date)
bench_ret = compute_benchmark_returns(bench_prices)

# Align benchmark to strategy dates
bench_ret = bench_ret.reindex(net_returns.index).fillna(0.0)

alpha_ann, beta = alpha_beta(net_returns, bench_ret)
ir = information_ratio(net_returns, bench_ret)
te = tracking_error(net_returns, bench_ret)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Alpha (annual)", f"{alpha_ann:.2%}")
c2.metric("Beta", f"{beta:.2f}")
c3.metric("Information Ratio", f"{ir:.2f}")
c4.metric("Tracking Error", f"{te:.2%}")

st.subheader("📈 Strategy vs Benchmark Equity")
bench_eq = equity_from_returns(bench_ret)

fig_b, ax_b = plt.subplots()
ax_b.plot(equity, label="Strategy")
ax_b.plot(bench_eq, label=bench_symbol)
ax_b.set_title("Equity Curve Comparison")
ax_b.set_xlabel("Date")
ax_b.set_ylabel("Normalized Equity")
ax_b.legend()
st.pyplot(fig_b)



# =============================
# Anomaly Spread Dashboard (NEW FEATURE)
# =============================
st.header("📌 Anomaly Spread (Long–Short)")

st.caption("Decomposes the strategy into Long leg, Short leg, and Long–Short spread with summary stats.")

# Compute leg returns from your existing prices + positions
long_ret, short_ret, spread_ret = leg_returns(prices, positions)

# Show stats table
stats_df = summary_table(long_ret, short_ret, spread_ret)

st.subheader("📋 Long/Short/Spread Summary")
st.dataframe(
    stats_df.style.format({
        "Ann Return": "{:.2%}",
        "Ann Vol": "{:.2%}",
        "Sharpe": "{:.2f}",
        "t-stat": "{:.2f}"
    })
)

# Plot leg returns cumulative equity
st.subheader("📈 Long vs Short vs Spread (Equity Curves)")

def _eq_from_ret(r):
    r = pd.Series(r).fillna(0.0)
    eq = (1.0 + r).cumprod()
    if len(eq) == 0:
        return eq
    return eq / eq.iloc[0]

eq_long = _eq_from_ret(long_ret)
eq_short = _eq_from_ret(short_ret)
eq_spread = _eq_from_ret(spread_ret)

fig_ls, ax_ls = plt.subplots()
ax_ls.plot(eq_long, label="Long")
ax_ls.plot(eq_short, label="Short")
ax_ls.plot(eq_spread, label="Long–Short")
ax_ls.set_title("Leg Equity Curves")
ax_ls.set_xlabel("Date")
ax_ls.set_ylabel("Normalized Equity")
ax_ls.legend()
st.pyplot(fig_ls)


# =============================
# Download Report (NEW FEATURE)
# =============================
st.header("📄 Download Strategy Report")

# Strategy settings summary
settings = {
    "Username": st.session_state.get("username", ""),
    "Factors": ", ".join([x for x, flag in [
        ("Momentum", use_momentum),
        ("Value", use_value),
        ("Profitability", use_profit),
    ] if flag]),
    "Transaction Cost (bps)": cost_bps,
    "Rebalance Frequency": rebalance_freq,
    "Data Source": "Yahoo Finance" if use_live else "Local CSV",
}

# Metric summary
metrics = {
    "Sharpe Ratio": f"{sharpe:.2f}",
    "Max Drawdown": f"{mdd:.2%}",
    "Final Equity": f"{equity.iloc[-1]:.2f}",
    "Avg Turnover": f"{avg_turnover:.2f}",
    "Benchmark": bench_symbol,
    "Alpha (annual)": f"{alpha_ann:.2%}",
    "Beta": f"{beta:.2f}",
    "Information Ratio": f"{ir:.2f}",
    "Tracking Error": f"{te:.2%}",
}

# Re-create figures for the report (so they embed cleanly)
fig_r1, ax_r1 = plt.subplots()
ax_r1.plot(equity)
ax_r1.set_title("Equity Curve (Net of Costs)")
ax_r1.set_xlabel("Date")
ax_r1.set_ylabel("Portfolio Value")

fig_r2, ax_r2 = plt.subplots()
ax_r2.plot(turnover)
ax_r2.set_title("Turnover Over Time")
ax_r2.set_xlabel("Date")
ax_r2.set_ylabel("Turnover")

# Benchmark figure
fig_r3, ax_r3 = plt.subplots()
ax_r3.plot(equity, label="Strategy")
ax_r3.plot(bench_eq, label=bench_symbol)
ax_r3.set_title("Strategy vs Benchmark Equity")
ax_r3.set_xlabel("Date")
ax_r3.set_ylabel("Normalized Equity")
ax_r3.legend()

# Long/Short/Spread figure
fig_r4, ax_r4 = plt.subplots()
ax_r4.plot(eq_long, label="Long")
ax_r4.plot(eq_short, label="Short")
ax_r4.plot(eq_spread, label="Long–Short")
ax_r4.set_title("Long vs Short vs Spread (Equity Curves)")
ax_r4.set_xlabel("Date")
ax_r4.set_ylabel("Normalized Equity")
ax_r4.legend()

html = build_html_report(
    title="Quant Research Platform — Strategy Report",
    settings=settings,
    metrics=metrics,
    figures=[
        ("Equity Curve", fig_r1),
        ("Turnover", fig_r2),
        ("Benchmark Comparison", fig_r3),
        ("Long/Short/Spread", fig_r4),
    ]
)

st.download_button(
    label="⬇️ Download HTML Report",
    data=html,
    file_name="strategy_report.html",
    mime="text/html",
)

pdf_bytes = build_pdf_report(
    title="Quant Research Platform — Strategy Report",
    settings=settings,
    metrics=metrics,
    figures=[
        ("Equity Curve", fig_r1),
        ("Turnover", fig_r2),
        ("Benchmark Comparison", fig_r3),
        ("Long/Short/Spread", fig_r4),
    ]
)

st.download_button(
    label="⬇️ Download PDF Report",
    data=pdf_bytes,
    file_name="strategy_report.pdf",
    mime="application/pdf",
)




 