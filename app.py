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
st.set_page_config(page_title="Quant Trading Platform", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(132,204,22,0.18), transparent 28%),
            radial-gradient(circle at top right, rgba(34,197,94,0.14), transparent 25%),
            linear-gradient(135deg, #fafaf5 0%, #f7f8f0 55%, #eef7e8 100%);
    }

    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 3rem;
        max-width: 1480px;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #fafaf5 0%, #f1f5e8 100%);
        border-right: 1px solid rgba(63,98,18,0.12);
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #1f2937 !important;
    }

    .top-nav {
        background: rgba(255,255,255,0.86);
        border: 1px solid rgba(100,116,139,0.18);
        border-radius: 22px;
        padding: 14px 22px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 12px 30px rgba(15,23,42,0.06);
        margin-bottom: 12px;
    }

    .brand-wrap {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .brand-logo {
        width: 46px;
        height: 46px;
        border-radius: 14px;
        background: linear-gradient(135deg, #3f7d20, #84cc16);
        box-shadow: 0 8px 20px rgba(63,125,32,0.25);
    }

    .brand-name {
        font-size: 1.25rem;
        font-weight: 900;
        color: #111827;
    }

    .nav-pill {
        display: inline-block;
        padding: 10px 18px;
        border-radius: 14px;
        border: 1px solid rgba(100,116,139,0.22);
        color: #111827;
        font-weight: 700;
        margin-left: 6px;
        background: rgba(255,255,255,0.72);
    }

    .ticker-strip {
        background: rgba(255,255,255,0.86);
        border: 1px solid rgba(100,116,139,0.14);
        border-radius: 18px;
        padding: 10px 18px;
        margin-bottom: 26px;
        box-shadow: 0 8px 24px rgba(15,23,42,0.05);
        white-space: nowrap;
        overflow: hidden;
    }

    .ticker-label {
        color: #64748b;
        font-weight: 800;
        margin-right: 18px;
    }

    .ticker-item {
        color: #111827;
        font-weight: 800;
        margin-right: 24px;
    }

    .up {
        background: #e7f4d8;
        color: #3f7d20;
        padding: 3px 9px;
        border-radius: 999px;
        margin-left: 5px;
    }

    .down {
        background: #fee2e2;
        color: #dc2626;
        padding: 3px 9px;
        border-radius: 999px;
        margin-left: 5px;
    }

    .welcome-title {
        font-size: 2.15rem;
        font-weight: 950;
        color: #111827;
        letter-spacing: -0.04em;
        margin-bottom: 4px;
    }

    .welcome-subtitle {
        color: #4b5563;
        font-size: 1.05rem;
        margin-bottom: 22px;
    }

    .kpi-card {
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(100,116,139,0.16);
        border-radius: 22px;
        padding: 24px 26px;
        box-shadow: 0 10px 28px rgba(15,23,42,0.06);
        min-height: 145px;
    }

    .kpi-label {
        color: #4b5563;
        font-weight: 800;
        font-size: 1rem;
        margin-bottom: 12px;
    }

    .kpi-value {
        color: #111827;
        font-size: 2rem;
        font-weight: 950;
        letter-spacing: -0.03em;
    }

    .kpi-note-green {
        display: inline-block;
        background: #e7f4d8;
        color: #3f7d20;
        padding: 4px 10px;
        border-radius: 8px;
        font-weight: 800;
        margin-top: 8px;
    }

    .kpi-note-red {
        display: inline-block;
        background: #fee2e2;
        color: #dc2626;
        padding: 4px 10px;
        border-radius: 8px;
        font-weight: 800;
        margin-top: 8px;
    }

    .panel {
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(100,116,139,0.16);
        border-radius: 24px;
        padding: 26px;
        box-shadow: 0 12px 32px rgba(15,23,42,0.07);
        margin-bottom: 22px;
    }

    .panel-title {
        font-size: 1.35rem;
        font-weight: 950;
        color: #111827;
        margin-bottom: 14px;
    }

    .mini-card {
        background: #f5f5ed;
        border-radius: 16px;
        padding: 18px;
        border: 1px solid rgba(100,116,139,0.10);
    }

    .mini-title {
        font-weight: 900;
        color: #111827;
        font-size: 1rem;
    }

    .mini-sub {
        color: #6b7280;
        margin-top: 4px;
    }

    .buy-pill {
        display: inline-block;
        background: #e7f4d8;
        color: #3f7d20;
        padding: 4px 12px;
        border-radius: 999px;
        font-weight: 900;
        margin-top: 10px;
    }

    .sell-pill {
        display: inline-block;
        background: #fee2e2;
        color: #dc2626;
        padding: 4px 12px;
        border-radius: 999px;
        font-weight: 900;
        margin-top: 10px;
    }

    .news-row {
        border-bottom: 1px solid rgba(100,116,139,0.18);
        padding: 14px 0;
    }

    .news-dot-green {
        display: inline-block;
        width: 10px;
        height: 10px;
        background: #3f7d20;
        border-radius: 50%;
        margin-right: 12px;
    }

    .news-dot-red {
        display: inline-block;
        width: 10px;
        height: 10px;
        background: #ef4444;
        border-radius: 50%;
        margin-right: 12px;
    }

    .news-title {
        font-size: 1.05rem;
        font-weight: 850;
        color: #111827;
    }

    .news-source {
        color: #6b7280;
        font-weight: 700;
        margin-left: 24px;
    }

    .quick-trade {
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(100,116,139,0.16);
        border-radius: 24px;
        padding: 26px;
        box-shadow: 0 12px 32px rgba(15,23,42,0.07);
    }

    .quick-button {
        background: #e7f4d8;
        color: #3f7d20;
        text-align: center;
        border-radius: 14px;
        padding: 12px;
        font-weight: 950;
        margin-bottom: 18px;
        font-size: 1.2rem;
    }

    .feature-card {
        background: rgba(255,255,255,0.9);
        padding: 24px;
        border-radius: 22px;
        box-shadow: 0 10px 28px rgba(15,23,42,0.08);
        border: 1px solid rgba(148,163,184,0.25);
        min-height: 160px;
    }

    .feature-title {
        font-size: 1.12rem;
        font-weight: 800;
        color: #111827;
        margin-bottom: 8px;
    }

    .feature-text {
        color: #64748b;
        font-size: 0.95rem;
        line-height: 1.45;
    }

    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(148,163,184,0.25);
        padding: 18px 20px;
        border-radius: 18px;
        box-shadow: 0 8px 22px rgba(15,23,42,0.06);
    }

    [data-testid="stMetricValue"] {
        font-size: 1.55rem;
        font-weight: 800;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =============================
# Authentication
# =============================
st.sidebar.header("👤 Account")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None


# =============================
# Premium cinematic landing page
# =============================

st.markdown("""
<style>

.space-hero {
    text-align: center;
    padding: 90px 30px;
    border-radius: 30px;
    background:
        radial-gradient(circle at top, rgba(59,130,246,0.40), transparent 35%),
        radial-gradient(circle at bottom, rgba(245,158,11,0.22), transparent 35%),
        linear-gradient(180deg,#020617 0%,#0f172a 100%);
    color: white;
    margin-bottom: 30px;
    box-shadow: 0px 20px 60px rgba(0,0,0,0.45);
}

.hero-badge {
    display:inline-block;
    padding:8px 18px;
    border-radius:999px;
    background:rgba(255,255,255,0.08);
    border:1px solid rgba(255,255,255,0.15);
    color:#93c5fd;
    font-weight:700;
    margin-bottom:20px;
}

.space-title {
    font-size:64px;
    font-weight:900;
    color:white;
    margin-bottom:20px;
    line-height:1.1;
}

.space-subtitle {
    font-size:20px;
    color:#cbd5e1;
    max-width:900px;
    margin:auto;
    line-height:1.7;
}

.cta-row {
    margin-top:35px;
}

.cta-primary {
    background:white;
    color:black;
    padding:14px 30px;
    border-radius:999px;
    font-weight:900;
    box-shadow:0 0 35px rgba(96,165,250,0.45);
}

.future-line {
    text-align:center;
    color:white;
    letter-spacing:6px;
    font-size:22px;
    font-weight:800;
    margin-top:55px;
}

.feature-card-dark {
    background: linear-gradient(180deg, rgba(15,23,42,0.95), rgba(2,6,23,0.95));
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 22px;
    padding: 24px;
    min-height: 145px;
    box-shadow: 0 18px 45px rgba(0,0,0,0.35);
}

.feature-card-title {
    color: white;
    font-size: 1.15rem;
    font-weight: 900;
    margin-bottom: 10px;
}

.feature-card-text {
    color: #94a3b8;
    font-size: 0.95rem;
    line-height: 1.5;
}

</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="space-hero">

<div class="hero-badge">
🚀 Advanced AI-Driven Quantitative Trading Platform
</div>

<div class="space-title">
TradePro Quant Fund
</div>

<div class="space-subtitle">
A systematic quant research platform built for portfolio optimization,
Monte Carlo simulation, risk analytics, market anomaly detection,
algorithmic trading research, and AI-powered investment strategies.
</div>

<div class="cta-row">
<span class="cta-primary">Scroll Down to Platform</span>
</div>

<div class="future-line">
THE FUTURE OF QUANTITATIVE TRADING
</div>

</div>
""", unsafe_allow_html=True)

nav1, nav2, nav3, nav4 = st.columns(4)

with nav1:
    st.page_link("pages/0_dashboard.py", label="Open Dashboard", icon="📊")

with nav2:
    st.page_link("pages/4_Market_Prices.py", label="Market Prices", icon="📈")

with nav3:
    st.page_link("pages/9_RiskEngine.py", label="Risk Engine", icon="🛡️")

with nav4:
    st.page_link("pages/11_MonteCarlo.py", label="Monte Carlo", icon="🎲")


f1, f2, f3, f4 = st.columns(4)

with f1:
    st.markdown("""
    <div class="feature-card-dark">
        <div class="feature-card-title">🛡️ Risk Engine</div>
        <div class="feature-card-text">
        Drawdown, volatility, Sharpe ratio, worst-period loss, and kill-switch monitoring.
        </div>
    </div>
    """, unsafe_allow_html=True)

with f2:
    st.markdown("""
    <div class="feature-card-dark">
        <div class="feature-card-title">🎲 Monte Carlo</div>
        <div class="feature-card-text">
        Forward portfolio simulations, scenario analysis, and probability-based forecasting.
        </div>
    </div>
    """, unsafe_allow_html=True)

with f3:
    st.markdown("""
    <div class="feature-card-dark">
        <div class="feature-card-title">📊 Optimizer</div>
        <div class="feature-card-text">
        Max Sharpe, minimum volatility, equal-weight, and risk-parity portfolio construction.
        </div>
    </div>
    """, unsafe_allow_html=True)

with f4:
    st.markdown("""
    <div class="feature-card-dark">
        <div class="feature-card-title">⚡ Trading Sim</div>
        <div class="feature-card-text">
        Simulated execution, positions, orders, performance tracking, and trading workflow.
        </div>
    </div>
    """, unsafe_allow_html=True)

# =============================
# Landing Page Visual Preview
# =============================
st.markdown("<br>", unsafe_allow_html=True)

v1, v2 = st.columns([1.5, 1])

with v1:
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(15,23,42,0.96), rgba(30,64,175,0.75));
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 28px;
        padding: 28px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.35);
    ">
        <div style="color:white; font-size:1.5rem; font-weight:900; margin-bottom:8px;">
            📈 Strategy Performance Preview
        </div>
        <div style="color:#94a3b8; margin-bottom:18px;">
            Simulated quant portfolio equity curve with risk-aware execution logic.
        </div>
    </div>
    """, unsafe_allow_html=True)

    preview_df = pd.DataFrame({
        "Equity Curve": [100, 103, 101, 108, 115, 112, 121, 132, 129, 141, 153, 160]
    })

    st.line_chart(preview_df)

with v2:
    st.markdown("""
<div style="background: radial-gradient(circle at top, rgba(245,158,11,0.25), transparent 35%), linear-gradient(180deg, rgba(15,23,42,0.98), rgba(2,6,23,0.98)); border: 1px solid rgba(255,255,255,0.14); border-radius: 28px; padding: 28px; box-shadow: 0 20px 60px rgba(0,0,0,0.35); min-height: 345px;">
<h3 style="color:white; font-size:1.4rem; font-weight:900; margin-bottom:18px;">🧠 Quant Modules</h3>
<p style="color:#cbd5e1; margin-bottom:14px;">● Monte Carlo Forecasting</p>
<p style="color:#cbd5e1; margin-bottom:14px;">● Portfolio Optimization</p>
<p style="color:#cbd5e1; margin-bottom:14px;">● Market Regime Detection</p>
<p style="color:#cbd5e1; margin-bottom:14px;">● Risk Monitoring Engine</p>
<p style="color:#cbd5e1; margin-bottom:14px;">● Trading Simulation</p>
<div style="margin-top:24px; background:rgba(255,255,255,0.08); border-radius:16px; padding:14px; color:#93c5fd; font-weight:800;">
System Status: Research Terminal Online
</div>
</div>
""", unsafe_allow_html=True)

# =============================
# Logout
# =============================
st.sidebar.success(f"Logged in as: {st.session_state.username}")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()


# =============================
# Research app header
# =============================
st.header("📊 Cost-Aware Quant Research Platform")
st.markdown(
    """
This page runs a long-short factor research pipeline with realistic transaction costs,
rebalancing, benchmark comparison, risk analytics, trade blotter, and report downloads.
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

    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw["Close"].to_frame()

    prices = prices.dropna()

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
raw_positions = generate_positions(combo).shift(1).fillna(0)

reb_dates = get_rebalance_dates(raw_positions.index, freq=rebalance_freq)
positions = apply_rebalance_rule(raw_positions, reb_dates)

turnover = compute_turnover(positions)
avg_turnover = turnover.mean()

raw_returns = compute_returns(prices, positions)
costs = apply_transaction_costs(positions, cost_rate)
net_returns = raw_returns - costs

equity = compute_equity_curve(net_returns)
equity = equity / equity.iloc[0]

st.session_state["strategy_returns"] = net_returns.dropna()
st.session_state["equity_curve"] = equity.dropna()
st.session_state["initial_capital"] = 1.0


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
# Holdings + Trade Blotter
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
    st.info("No trades found. Try lowering the threshold or changing rebalance frequency.")
else:
    st.caption("Trade = NewWeight − PrevWeight. Positive = buy more / cover short. Negative = sell / short more.")
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
# Benchmark Dashboard
# =============================
st.header("📌 Benchmark Dashboard (SPY / QQQ)")

bench_symbol = st.selectbox("Benchmark", ["SPY", "QQQ", "IWM", "DIA"], index=0)

start_date = "2018-01-01"
if len(prices.index) > 0:
    start_date = str(prices.index.min().date())

bench_prices = load_benchmark_prices(symbol=bench_symbol, start=start_date)
bench_ret = compute_benchmark_returns(bench_prices)

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
# Anomaly Spread Dashboard
# =============================
st.header("📌 Anomaly Spread (Long–Short)")

st.caption("Decomposes the strategy into Long leg, Short leg, and Long–Short spread with summary stats.")

long_ret, short_ret, spread_ret = leg_returns(prices, positions)

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
# Download Report
# =============================
st.header("📄 Download Strategy Report")

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

fig_r3, ax_r3 = plt.subplots()
ax_r3.plot(equity, label="Strategy")
ax_r3.plot(bench_eq, label=bench_symbol)
ax_r3.set_title("Strategy vs Benchmark Equity")
ax_r3.set_xlabel("Date")
ax_r3.set_ylabel("Normalized Equity")
ax_r3.legend()

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