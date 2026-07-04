import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt      # kept for PDF/HTML report export only
import plotly.graph_objects as go
import yfinance as yf

from components.layout import setup_page, section, next_step, plotly_config

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
from backtest.legs import leg_returns
from backtest.anomaly_stats import summary_table
from backtest.benchmark import alpha_beta, information_ratio, tracking_error, equity_from_returns
from backtest.ic import information_coefficient, ic_decay, ic_summary, icir as compute_icir
from backtest.walk_forward import walk_forward_backtest

from data.benchmark import load_benchmark_prices, compute_benchmark_returns

from portfolio.blotter import holdings_snapshot, trade_blotter

from reports.report import build_html_report
from reports.pdf import build_pdf_report

from stratergy_store import save_strategy, load_strategies
from core.context import StrategyContext, save_context


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
# Sidebar controls (grouped with expanders)
# =============================
with st.sidebar.expander("⚙️ Strategy", expanded=True):
    use_momentum = st.checkbox("Momentum", True)
    use_value    = st.checkbox("Value",    True)
    use_profit   = st.checkbox("Profitability", True)
    st.divider()
    cost_bps = st.slider("Transaction Cost (bps)", 0, 50, 10, step=5)

cost_rate = cost_bps / 10_000

with st.sidebar.expander("📅 Rebalance"):
    rebalance_freq = st.selectbox(
        "Frequency",
        ["D", "W", "M", "Q"],
        index=2,
    )

with st.sidebar.expander("🌍 Data Source"):
    use_live = st.checkbox("Use Live Market Data (Yahoo Finance)")

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
section("Portfolio Construction", "Generate positions, apply rebalancing, transaction costs, and compute net strategy returns.")

raw_positions = generate_positions(combo).shift(1).fillna(0)
reb_dates = get_rebalance_dates(raw_positions.index, freq=rebalance_freq)
positions = apply_rebalance_rule(raw_positions, reb_dates)

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

# Save for other pages (and persist to disk so data survives refresh)
_eq_save = equity.dropna()
_ret_save = net_returns.dropna()
st.session_state["strategy_returns"] = _ret_save
st.session_state["equity_curve"]     = _eq_save
st.session_state["initial_capital"]  = 1.0

try:
    from session_persist import save_session
    save_session(_eq_save, _ret_save, 1.0)
except Exception:
    pass

# ── Persist full StrategyContext for cross-page use ───────────────────────────
_ctx = StrategyContext(
    tickers        = list(prices.columns),
    start_date     = str(prices.index.min().date()) if len(prices.index) > 0 else "",
    end_date       = str(prices.index.max().date()) if len(prices.index) > 0 else "",
    prices         = prices,
    signal         = combo,
    positions      = positions,
    gross_returns  = raw_returns,
    net_returns    = net_returns,
    equity_curve   = equity,
    strategy_name  = "_".join(selected_factors) if selected_factors else "Unnamed",
    signals_used   = selected_factors,
    cost_bps       = float(cost_bps),
    rebalance_freq = rebalance_freq,
)
save_context(_ctx)

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
# Save Strategy (sidebar)
# =============================
st.sidebar.divider()
with st.sidebar.expander("💾 Save Strategy"):
    if st.button("Save Current Strategy", use_container_width=True):
        payload = {
            "signals": selected_factors,
            "user_id": st.session_state.get("username", "anonymous"),
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
        uname = st.session_state.get("username", "anonymous")
        save_strategy(f"{uname}_strategy", payload)
        st.success("Strategy saved!")

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

fig_eq = go.Figure(go.Scatter(x=equity.index, y=equity.values, mode="lines", name="Equity",
                               line=dict(color="#10b981", width=2),
                               fill="tozeroy", fillcolor="rgba(16,185,129,0.07)"))
fig_eq.update_layout(title="Equity Curve (Net of Costs)", xaxis_title="Date",
                     yaxis_title="Portfolio Value", **plotly_config())
st.plotly_chart(fig_eq, use_container_width=True)

# Underwater (drawdown) chart immediately below equity curve
_dd_bt = equity / equity.cummax() - 1
fig_uw = go.Figure(go.Scatter(
    x=_dd_bt.index, y=_dd_bt.values,
    mode="lines", name="Drawdown",
    line=dict(color="#ef4444", width=1.5),
    fill="tozeroy", fillcolor="rgba(239,68,68,0.12)",
))
fig_uw.add_hline(y=float(mdd), line_dash="dash", line_color="#f59e0b", line_width=1,
                 annotation_text=f"Max DD: {mdd:.2%}",
                 annotation_position="bottom right",
                 annotation_font_color="#f59e0b")
fig_uw.update_layout(title="Underwater (Drawdown) Chart", xaxis_title="Date",
                     yaxis_title="Drawdown", **plotly_config(height=200, margin=dict(l=10,r=10,t=44,b=10)))
st.plotly_chart(fig_uw, use_container_width=True)

st.divider()

# =============================
# Turnover
# =============================
section("Portfolio Turnover", "How much the portfolio changes over time.")

fig_to = go.Figure(go.Scatter(x=turnover.index, y=turnover.values, mode="lines", name="Turnover",
                               line=dict(color="#3b82f6", width=2)))
fig_to.update_layout(title="Turnover Over Time", xaxis_title="Date",
                     yaxis_title="Turnover", **plotly_config())
st.plotly_chart(fig_to, use_container_width=True)

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

st.divider()

# =============================
# Holdings & Trade Blotter
# =============================
section("Holdings & Trade Blotter", "Current portfolio snapshot and rebalance trade log.")

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

st.divider()

# =============================
# Saved strategies
# =============================
section("My Saved Strategies", "Strategies saved across sessions.")

saved = load_strategies()

if not saved.empty:
    st.dataframe(saved)
else:
    st.info("No saved strategies yet.")

st.divider()

# =============================
# Risk Dashboard
# =============================
section("Risk Dashboard", "Rolling volatility, rolling Sharpe, drawdown profile, and worst monthly returns.")

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

fig_vol = go.Figure(go.Scatter(x=rolling_vol.index, y=rolling_vol.values, mode="lines",
                               name="Rolling Vol", line=dict(color="#f59e0b", width=2)))
fig_vol.update_layout(title=f"{rolling_window}-Month Rolling Volatility",
                      xaxis_title="Date", yaxis_title="Volatility", **plotly_config())
st.plotly_chart(fig_vol, use_container_width=True)

fig_rs = go.Figure(go.Scatter(x=rolling_sharpe.index, y=rolling_sharpe.values, mode="lines",
                               name="Rolling Sharpe", line=dict(color="#3b82f6", width=2)))
fig_rs.update_layout(title=f"{rolling_window}-Month Rolling Sharpe Ratio",
                     xaxis_title="Date", yaxis_title="Sharpe", **plotly_config())
st.plotly_chart(fig_rs, use_container_width=True)

st.subheader("📉 Drawdown Analysis")

drawdown = equity / equity.cummax() - 1

fig_dd = go.Figure(go.Scatter(x=drawdown.index, y=drawdown.values, mode="lines",
                               name="Drawdown", line=dict(color="#ef4444", width=2),
                               fill="tozeroy", fillcolor="rgba(239,68,68,0.08)"))
fig_dd.update_layout(title="Drawdown Over Time", xaxis_title="Date",
                     yaxis_title="Drawdown", **plotly_config())
st.plotly_chart(fig_dd, use_container_width=True)

st.subheader("📆 Worst Monthly Returns")

_monthly_bt = net_returns.groupby([net_returns.index.year, net_returns.index.month]).apply(
    lambda x: (1 + x).prod() - 1
)
_monthly_bt.index.names = ["Year", "Month"]
worst_months = _monthly_bt.nsmallest(5)
st.dataframe(worst_months.rename("Monthly Return"))

st.divider()

# Monthly returns heatmap
section("Monthly Returns Heatmap", "Calendar view of monthly returns — red = loss, green = gain.")

_month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
_pivot_df = _monthly_bt.reset_index()
_pivot_df.columns = ["Year", "Month", "Return"]
_pivot = _pivot_df.pivot(index="Year", columns="Month", values="Return")
_pivot.columns = [_month_names[c - 1] for c in _pivot.columns]
_pivot.index = _pivot.index.astype(str)

_z_raw = _pivot.values * 100
_text_heat = [
    [f"{v:.1f}%" if v == v else "" for v in row]  # nan-safe
    for row in _z_raw.tolist()
]
fig_heat = go.Figure(go.Heatmap(
    z=_z_raw.tolist(),
    x=_pivot.columns.tolist(),
    y=_pivot.index.tolist(),
    colorscale="RdYlGn",
    zmid=0,
    text=_text_heat,
    texttemplate="%{text}",
    hovertemplate="Year: %{y} | %{x} | Return: %{z:.2f}%<extra></extra>",
    colorbar=dict(title="Return %", thickness=14, tickfont=dict(color="#e2e8f0")),
))
fig_heat.update_layout(
    title="Monthly Returns Heatmap (%)",
    xaxis_title="Month", yaxis_title="Year",
    **plotly_config(margin=dict(l=10, r=10, t=44, b=40)),
)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# Daily return distribution histogram
section("Daily Return Distribution", "Histogram of net daily returns with mean and ±1σ markers.")

_mean_r = float(net_returns.mean())
_std_r  = float(net_returns.std())

fig_hist_bt = go.Figure()
fig_hist_bt.add_trace(go.Histogram(
    x=net_returns.values, nbinsx=40,
    marker_color="#3b82f6", opacity=0.78, name="Daily Returns",
))
fig_hist_bt.add_vline(x=_mean_r, line_dash="solid", line_color="#10b981", line_width=2,
                      annotation_text=f"Mean: {_mean_r:.4f}",
                      annotation_position="top right",
                      annotation_font_color="#10b981")
fig_hist_bt.add_vline(x=_mean_r - _std_r, line_dash="dash", line_color="#f59e0b", line_width=1,
                      annotation_text=f"−1σ",
                      annotation_position="top left",
                      annotation_font_color="#f59e0b")
fig_hist_bt.add_vline(x=_mean_r + _std_r, line_dash="dash", line_color="#f59e0b", line_width=1,
                      annotation_text=f"+1σ",
                      annotation_position="top right",
                      annotation_font_color="#f59e0b")
fig_hist_bt.update_layout(
    title="Daily Return Distribution",
    xaxis_title="Daily Return", yaxis_title="Frequency",
    **plotly_config(),
)
st.plotly_chart(fig_hist_bt, use_container_width=True)

st.divider()

# =============================
# Parameter Sensitivity Analysis
# =============================
section("Parameter Sensitivity (Robustness Test)", "Stress-test performance across different transaction cost levels.")

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

if not sens_df.empty:
    st.subheader("📈 Performance vs Transaction Costs")

    fig_sens = go.Figure(go.Scatter(x=sens_df["Cost (bps)"], y=sens_df["Sharpe"],
                                    mode="lines+markers", name="Sharpe",
                                    line=dict(color="#10b981", width=2),
                                    marker=dict(size=7)))
    fig_sens.update_layout(title="Sharpe Sensitivity to Transaction Costs",
                           xaxis_title="Transaction Cost (bps)", yaxis_title="Sharpe Ratio",
                           **plotly_config())
    st.plotly_chart(fig_sens, use_container_width=True)

st.divider()

# =============================
# Strategy Comparison Playground
# =============================
section("Strategy Comparison Playground", "Compare individual factor strategies and the composite side-by-side.")

strategies = {
    "Momentum": [momentum_signal(prices)],
    "Value": [value_signal(book, mcap)],
    "Profitability": [profitability_signal(gprofit, mcap)],
    "Composite": signal_list,
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

fig_cmp = go.Figure()
colors = ["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6"]
for i, name in enumerate(selected):
    ec = equity_curves[name]
    fig_cmp.add_trace(go.Scatter(x=ec.index, y=ec.values, mode="lines",
                                  name=name, line=dict(color=colors[i % len(colors)], width=2)))
fig_cmp.update_layout(title="Equity Curve Comparison", xaxis_title="Date",
                      yaxis_title="Normalized Equity", **plotly_config())
st.plotly_chart(fig_cmp, use_container_width=True)

st.divider()

# =============================
# Benchmark Dashboard
# =============================
section("Benchmark Dashboard (SPY / QQQ)", "Compare strategy against a market benchmark.")

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

cb1, cb2, cb3, cb4 = st.columns(4)
cb1.metric("Alpha (annual)", f"{alpha_ann:.2%}")
cb2.metric("Beta", f"{beta:.2f}")
cb3.metric("Information Ratio", f"{ir:.2f}")
cb4.metric("Tracking Error", f"{te:.2%}")

st.subheader("📈 Strategy vs Benchmark Equity")
bench_eq = equity_from_returns(bench_ret)

fig_b = go.Figure()
fig_b.add_trace(go.Scatter(x=equity.index,    y=equity.values,    mode="lines",
                            name="Strategy",   line=dict(color="#10b981", width=1.5)))
fig_b.add_trace(go.Scatter(x=bench_eq.index,  y=bench_eq.values,  mode="lines",
                            name=bench_symbol, line=dict(color="#3b82f6", width=1.5)))
fig_b.update_layout(title="Strategy vs Benchmark Equity", xaxis_title="Date",
                    yaxis_title="Normalized Equity", showlegend=True, **plotly_config())

# Stats strip above chart
_strat_norm = equity
if len(_strat_norm) > 5:
    import numpy as np
    _cagr = float((_strat_norm.iloc[-1] ** (252/len(_strat_norm)) - 1) * 100)
    _ann_ret = float((_strat_norm.pct_change().dropna().mean()) * 252 * 100)
    _ann_vol = float((_strat_norm.pct_change().dropna().std()) * (252**0.5) * 100)
    _sh = float(_strat_norm.pct_change().dropna().mean() / (_strat_norm.pct_change().dropna().std() + 1e-9) * (252**0.5))
    _dd = float((_strat_norm / _strat_norm.cummax() - 1).min() * 100)
    _stat_items = [("CAGR", f"{_cagr:.1f}%"), ("Ann. Return", f"{_ann_ret:.1f}%"),
                   ("Ann. Vol", f"{_ann_vol:.1f}%"), ("Sharpe", f"{_sh:.2f}"),
                   ("Max DD", f"{_dd:.1f}%")]
    _stat_cols = st.columns(len(_stat_items))
    for _sc, (_lbl, _sval) in zip(_stat_cols, _stat_items):
        _sc.markdown(f'''<div style="text-align:center;padding:8px 4px;background:rgba(13,20,33,0.60);
            border:1px solid rgba(245,158,11,0.10);border-radius:6px;">
            <div style="font-family:JetBrains Mono,monospace;font-size:0.50rem;color:#334155;
                text-transform:uppercase;letter-spacing:0.14em;">{_lbl}</div>
            <div style="font-family:JetBrains Mono,monospace;font-size:0.88rem;font-weight:700;
                color:#E2E8F0;margin-top:3px;">{_sval}</div>
            </div>''', unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

st.plotly_chart(fig_b, use_container_width=True, config={"displayModeBar": False})

st.divider()

# =============================
# Anomaly Spread Dashboard
# =============================
section("Anomaly Spread (Long–Short)", "Decomposes the strategy into Long leg, Short leg, and Long–Short spread with summary stats.")

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

fig_ls = go.Figure()
fig_ls.add_trace(go.Scatter(x=eq_long.index,   y=eq_long.values,   mode="lines",
                             name="Long",        line=dict(color="#10b981", width=2)))
fig_ls.add_trace(go.Scatter(x=eq_short.index,  y=eq_short.values,  mode="lines",
                             name="Short",       line=dict(color="#ef4444", width=2)))
fig_ls.add_trace(go.Scatter(x=eq_spread.index, y=eq_spread.values, mode="lines",
                             name="Long–Short",  line=dict(color="#3b82f6", width=2)))
fig_ls.update_layout(title="Leg Equity Curves", xaxis_title="Date",
                     yaxis_title="Normalized Equity", **plotly_config())
st.plotly_chart(fig_ls, use_container_width=True)

st.divider()

# =============================
# Download Report
# =============================
section("Download Strategy Report", "Export the full research report as HTML or PDF.")

settings = {
    "Username": st.session_state.get("username", ""),
    "Factors": ", ".join(selected_factors),
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

next_step("Open the Dashboard or Risk Engine next to monitor the saved backtest results.")

st.divider()

# =============================================================================
# IC Analysis — Signal Quality
# =============================================================================
section(
    "Signal Quality — Information Coefficient (IC)",
    "IC = Spearman rank correlation between the factor signal and forward returns. "
    "Mean IC > 0.02 and ICIR > 0.5 indicate a genuinely predictive factor.",
)

price_returns = prices.pct_change()
ic_ser = information_coefficient(combo, price_returns, horizon=1)

mean_ic   = float(ic_ser.mean())
std_ic    = float(ic_ser.std())
icir_val  = compute_icir(ic_ser)
t_stat_ic = float(mean_ic / (std_ic / np.sqrt(max(len(ic_ser.dropna()), 1))))

ica, icb, icc, icd = st.columns(4)
ica.metric("Mean IC (1-day)", f"{mean_ic:.4f}", help="IC > 0.02 is considered meaningful.")
icb.metric("IC Std",          f"{std_ic:.4f}")
icc.metric("ICIR",            f"{icir_val:.2f}", help="ICIR > 0.5 = strong factor.")
icd.metric("IC t-stat",       f"{t_stat_ic:.2f}", help="> 2.0 = statistically significant.")

# Save IC mean back into context
if "_strategy_context" in st.session_state:
    st.session_state["_strategy_context"].mean_ic = mean_ic

# Rolling IC chart
rolling_ic = ic_ser.rolling(21).mean()
fig_ic = go.Figure()
fig_ic.add_trace(go.Scatter(
    x=ic_ser.index, y=ic_ser.values,
    mode="lines", name="Daily IC",
    line=dict(color="#334155", width=1),
))
fig_ic.add_trace(go.Scatter(
    x=rolling_ic.index, y=rolling_ic.values,
    mode="lines", name="21-day Rolling Mean IC",
    line=dict(color="#06B6D4", width=2),
))
fig_ic.add_hline(y=0,    line_dash="dash", line_color="#475569")
fig_ic.add_hline(y=0.02, line_dash="dot",  line_color="#10B981",
                 annotation_text="IC=0.02 threshold", annotation_font_color="#10B981")
fig_ic.update_layout(
    title="IC Time Series (daily vs 21-day rolling mean)",
    xaxis_title="Date", yaxis_title="IC",
    **plotly_config(),
)
st.plotly_chart(fig_ic, use_container_width=True)

# IC Decay chart
with st.expander("IC Decay Analysis — how quickly does the signal lose predictive power?"):
    decay = ic_decay(combo, price_returns, max_horizon=20)
    colors = ["#10B981" if v > 0 else "#EF4444" for v in decay.values]
    fig_decay = go.Figure(go.Bar(
        x=[str(h) for h in decay.index],
        y=decay.values,
        marker_color=colors,
        text=[f"{v:.4f}" for v in decay.values],
        textposition="outside",
    ))
    fig_decay.add_hline(y=0, line_dash="dash", line_color="#475569")
    fig_decay.update_layout(
        title="Mean IC at Each Forward Horizon (days)",
        xaxis_title="Horizon (days)", yaxis_title="Mean IC",
        **plotly_config(),
    )
    st.plotly_chart(fig_decay, use_container_width=True)

# Full IC summary table
with st.expander("IC Summary Table (1, 3, 5, 10, 20 days)"):
    ic_tbl = ic_summary(combo, price_returns, horizons=[1, 3, 5, 10, 20])
    st.dataframe(
        ic_tbl.style.format({
            "Mean IC": "{:.4f}",
            "Std IC":  "{:.4f}",
            "ICIR":    "{:.3f}",
            "t-stat":  "{:.2f}",
        }).background_gradient(subset=["Mean IC"], cmap="RdYlGn", vmin=-0.05, vmax=0.05),
        use_container_width=True,
    )

st.divider()

# =============================================================================
# Walk-Forward Validation
# =============================================================================
section(
    "Walk-Forward Out-of-Sample Validation",
    "Signals are trained on a rolling window and tested on the NEXT unseen period only. "
    "This removes look-ahead bias — the critical flaw in a standard full-sample backtest.",
)

with st.sidebar.expander("🔁 Walk-Forward"):
    run_wf      = st.checkbox("Enable Walk-Forward", value=False, key="wf_enabled")
    wf_train_yr = st.slider("Train Window (years)", 1, 5, 3, key="wf_train_yr")
    wf_test_qtr = st.slider("Test Window (quarters)", 1, 4, 1, key="wf_test_qtr")

if not run_wf:
    st.info(
        "Enable **Walk-Forward** in the sidebar to run out-of-sample validation. "
        "This takes 10–30 seconds depending on the data range.",
        icon="ℹ️",
    )
else:
    with st.spinner("Running walk-forward validation — computing OOS returns per fold…"):

        def _wf_signal(p: pd.DataFrame) -> pd.DataFrame:
            sigs = []
            if use_momentum:
                sigs.append(momentum_signal(p))
            # Value / profitability require fundamentals; only include in local-CSV mode
            if not use_live and use_value:
                try:
                    b = book.reindex(p.index).ffill()
                    m = mcap.reindex(p.index).ffill()
                    sigs.append(value_signal(b, m))
                except Exception:
                    pass
            if not use_live and use_profit:
                try:
                    gp = gprofit.reindex(p.index).ffill()
                    m  = mcap.reindex(p.index).ffill()
                    sigs.append(profitability_signal(gp, m))
                except Exception:
                    pass
            if not sigs:
                return pd.DataFrame()
            return build_composite_signal(sigs)

        wf_result = walk_forward_backtest(
            prices                = prices,
            build_signal_fn       = _wf_signal,
            generate_positions_fn = generate_positions,
            compute_returns_fn    = compute_returns,
            apply_costs_fn        = lambda pos: apply_transaction_costs(pos, cost_rate),
            n_train               = int(wf_train_yr * 252),
            n_test                = int(wf_test_qtr * 63),
        )

    oos        = wf_result["oos_returns"]
    fold_data  = wf_result["fold_stats"]
    n_folds    = wf_result["n_folds"]

    if len(oos) == 0:
        st.warning(
            "Not enough data for walk-forward with current settings. "
            "Try reducing the train window or the date range."
        )
    else:
        oos_eq     = (1 + oos.fillna(0)).cumprod()
        oos_eq     = oos_eq / oos_eq.iloc[0]
        oos_std    = float(oos.std())
        oos_sharpe = float(oos.mean() / oos_std * np.sqrt(252)) if oos_std > 0 else 0.0
        oos_mdd    = float((oos_eq / oos_eq.cummax() - 1).min())
        oos_ret    = float(oos_eq.iloc[-1] - 1)

        wfa, wfb, wfc, wfd = st.columns(4)
        wfa.metric("OOS Sharpe",     f"{oos_sharpe:.2f}",
                   delta=f"{oos_sharpe - sharpe:+.2f} vs in-sample")
        wfb.metric("OOS Max DD",     f"{oos_mdd:.2%}")
        wfc.metric("OOS Total Ret",  f"{oos_ret:.2%}")
        wfd.metric("Folds",          str(n_folds))

        # OOS vs IS equity
        fig_wf = go.Figure()
        fig_wf.add_trace(go.Scatter(
            x=equity.index, y=equity.values,
            mode="lines", name="In-Sample (full backtest)",
            line=dict(color="#334155", width=1.5, dash="dot"),
        ))
        fig_wf.add_trace(go.Scatter(
            x=oos_eq.index, y=oos_eq.values,
            mode="lines", name="Out-of-Sample (walk-forward)",
            line=dict(color="#F59E0B", width=2),
        ))
        fig_wf.update_layout(
            title="In-Sample vs Out-of-Sample Equity Curves",
            xaxis_title="Date", yaxis_title="Normalized Value",
            **plotly_config(),
        )
        st.plotly_chart(fig_wf, use_container_width=True)

        if fold_data:
            folds_df = pd.DataFrame(fold_data)
            st.subheader("Fold-by-Fold Summary")
            st.dataframe(
                folds_df.style.format({
                    "OOS Sharpe": "{:.3f}",
                    "OOS Max DD": "{:.2%}",
                }).background_gradient(subset=["OOS Sharpe"], cmap="RdYlGn", vmin=-1, vmax=1),
                use_container_width=True,
            )

st.divider()
