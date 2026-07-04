import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf

from components.layout import setup_page, section, next_step, plotly_config

from execution.sim_broker import init_db
from execution.sim_performance import load_trades_df, equity_curve_from_trades


# =============================
# Page setup
# =============================
setup_page(
    "Performance Dashboard",
    "Analyze simulated trading performance, equity curve, drawdown, positions, and realized PnL.",
    "📊"
)


# =============================
# Initialize database
# =============================
init_db()


# =============================
# Load trades
# =============================
section("Trade Data", "Load simulated trade history from the paper trading system.")

df_trades = load_trades_df()

if df_trades is None or len(df_trades) == 0:
    st.info("No trades found yet. Place some simulated trades first.")
    st.stop()

st.success(f"Loaded {len(df_trades)} simulated trades.")

st.divider()


# =============================
# Price map helper
# =============================
def get_price_map(symbols):
    price_map = {}

    try:
        from market import prices

        i = 0
        while i < len(symbols):
            s = symbols[i]

            if hasattr(prices, "get_latest_price"):
                price_map[s] = float(prices.get_latest_price(s))

            i += 1

    except:
        pass

    return price_map


# =============================
# Build performance data
# =============================
symbols = sorted(list(set([str(x).upper() for x in df_trades["symbol"].tolist()])))

price_map = get_price_map(symbols)

if len(price_map) == 0:
    price_map = None

equity_df, stats, blotter, pos_df = equity_curve_from_trades(
    df_trades,
    price_map=price_map
)


# Save to global session state for other pages
if equity_df is not None and len(equity_df) > 0:
    equity_series = pd.Series(
        equity_df["equity"].values,
        index=pd.to_datetime(equity_df["date"])
    )

    returns_series = equity_series.pct_change().dropna()

    st.session_state["equity_curve"]     = equity_series
    st.session_state["strategy_returns"] = returns_series
    st.session_state["initial_capital"]  = float(stats["starting_cash"])

    try:
        from session_persist import save_session
        save_session(equity_series, returns_series, float(stats["starting_cash"]))
    except Exception:
        pass


# =============================
# KPIs
# =============================
section("Performance Summary", "Core simulated trading performance metrics.")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Starting Equity", f'${stats["starting_cash"]:,.2f}')
c2.metric("Ending Equity", f'${stats["ending_equity"]:,.2f}')
c3.metric("Total Return", f'{stats["total_return"]*100:.2f}%')
c4.metric("Max Drawdown", f'{stats["max_drawdown"]*100:.2f}%')

c5, c6, c7, c8 = st.columns(4)

c5.metric("Sharpe Daily", f'{stats["sharpe_daily"]:.2f}')
c6.metric("Win Rate", f'{stats["win_rate"]*100:.1f}%')
c7.metric("Profit Factor", f'{stats["profit_factor"]:.2f}')
c8.metric("Trades", str(stats["num_trades"]))

st.divider()


# =============================
# Performance insight
# =============================
section("Performance Insight")

if stats["total_return"] > 0 and stats["sharpe_daily"] > 1:
    st.success("The simulated strategy is profitable with strong risk-adjusted performance.")

elif stats["total_return"] > 0:
    st.info("The simulated strategy is profitable, but risk-adjusted performance should be reviewed.")

elif stats["max_drawdown"] < -0.10:
    st.warning("The strategy is currently negative and has meaningful drawdown risk.")

else:
    st.warning("The strategy is not currently profitable. Review trade selection, sizing, and execution.")

st.divider()


# =============================
# Equity curve plot
# =============================
section("Equity Curve", "Simulated account equity over time.")

fig = go.Figure(go.Scatter(
    x=pd.to_datetime(equity_df["date"]).tolist(),
    y=equity_df["equity"].tolist(),
    mode="lines",
    name="Equity",
    line=dict(color="#10b981", width=2)
))
fig.update_layout(title="Simulated Equity Curve", xaxis_title="Date", yaxis_title="Equity", **plotly_config())
st.plotly_chart(fig, use_container_width=True)

st.divider()


# =============================
# Drawdown
# =============================
section("Drawdown", "Peak-to-trough decline in simulated account value.")

peak = equity_df["equity"].cummax()
dd = (equity_df["equity"] / peak) - 1.0

dd_df = pd.DataFrame({
    "date": equity_df["date"],
    "drawdown": dd
})

fig2 = go.Figure(go.Scatter(
    x=pd.to_datetime(dd_df["date"]).tolist(),
    y=dd_df["drawdown"].tolist(),
    mode="lines",
    name="Drawdown",
    line=dict(color="#ef4444", width=2)
))
fig2.update_layout(title="Drawdown Curve", xaxis_title="Date", yaxis_title="Drawdown", **plotly_config())
st.plotly_chart(fig2, use_container_width=True)

st.divider()


# =============================
# Cumulative Returns vs SPY
# =============================
section("Cumulative Returns vs SPY", "Strategy equity normalised to 1.0 versus SPY buy-and-hold.")

_perf_dates = pd.to_datetime(equity_df["date"])
_strat_eq = pd.Series(equity_df["equity"].values, index=_perf_dates)
_strat_norm = _strat_eq / _strat_eq.iloc[0]


@st.cache_data(ttl=3600)
def _fetch_spy_perf(start_str, end_str):
    try:
        _raw = yf.download("SPY", start=start_str, end=end_str,
                           auto_adjust=True, progress=False)
        if _raw.empty:
            return pd.Series(dtype=float)
        _close = _raw["Close"].squeeze().dropna()
        return ((1 + _close.pct_change().dropna()).cumprod())
    except Exception:
        return pd.Series(dtype=float)


_spy_raw = _fetch_spy_perf(
    str(_perf_dates.min().date()),
    str((_perf_dates.max() + pd.Timedelta(days=1)).date()),
)

fig_cmp = go.Figure()
fig_cmp.add_trace(go.Scatter(
    x=_strat_norm.index, y=_strat_norm.values,
    mode="lines", name="Strategy",
    line=dict(color="#10b981", width=2),
    fill="tozeroy", fillcolor="rgba(16,185,129,0.06)",
))
if len(_spy_raw) > 1:
    _spy_aligned = _spy_raw.reindex(_strat_norm.index, method="ffill").dropna()
    if len(_spy_aligned) > 0:
        _spy_norm = _spy_aligned / _spy_aligned.iloc[0]
        fig_cmp.add_trace(go.Scatter(
            x=_spy_norm.index, y=_spy_norm.values,
            mode="lines", name="SPY",
            line=dict(color="#3b82f6", width=2, dash="dot"),
        ))
fig_cmp.update_layout(
    title="Cumulative Returns: Strategy vs SPY",
    xaxis_title="Date", yaxis_title="Cumulative Return (base = 1)",
    **plotly_config(),
)
st.plotly_chart(fig_cmp, use_container_width=True)

st.divider()


# =============================
# Rolling Sharpe
# =============================
section("Rolling Sharpe Ratio (21-day)", "21-day trailing Sharpe showing consistency of risk-adjusted returns over time.")

_perf_rets = _strat_eq.pct_change().dropna()
_roll_sharpe_perf = (
    _perf_rets.rolling(21).mean() / (_perf_rets.rolling(21).std() + 1e-9)
) * np.sqrt(252)

fig_rs = go.Figure()
fig_rs.add_trace(go.Scatter(
    x=_roll_sharpe_perf.index, y=_roll_sharpe_perf.values,
    mode="lines", name="Rolling Sharpe (21d)",
    line=dict(color="#8b5cf6", width=2),
))
fig_rs.add_hline(y=0, line_dash="solid", line_color="rgba(100,116,139,0.4)", line_width=1)
fig_rs.add_hline(y=1, line_dash="dot", line_color="#10b981", line_width=1,
                 annotation_text="Sharpe = 1", annotation_position="bottom right",
                 annotation_font_color="#10b981")
fig_rs.update_layout(
    title="21-Day Rolling Sharpe Ratio",
    xaxis_title="Date", yaxis_title="Sharpe Ratio",
    **plotly_config(),
)
st.plotly_chart(fig_rs, use_container_width=True)

st.divider()


# =============================
# Positions
# =============================
section("Open Positions", "Current simulated positions marked using available prices.")

if pos_df is None or len(pos_df) == 0:
    st.info("No open positions.")

else:
    st.dataframe(
        pos_df,
        use_container_width=True
    )

st.divider()


# =============================
# Trade blotter
# =============================
section("Trade Blotter", "Executed trades and realized PnL on sells.")

show = blotter.copy()

show["dt"] = show["dt"].astype(str)

st.dataframe(
    show[
        [
            "dt",
            "symbol",
            "side",
            "qty",
            "price",
            "realized_pl",
            "cash_after"
        ]
    ],
    use_container_width=True
)


# =============================
# Next step
# =============================
next_step(
    "Open Risk Engine, Monte Carlo, or Strategy DNA next to analyze this performance more deeply."
)
