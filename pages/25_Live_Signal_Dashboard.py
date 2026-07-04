"""
25_Live_Signal_Dashboard.py
Real-time factor signals for a chosen ticker universe.

Shows:
  - Current momentum percentile rank per ticker
  - LONG / SHORT / HOLD classification
  - Rank change vs yesterday (movers)
  - 60-day rolling rank heatmap
  - Optionally loads StrategyContext from a completed backtest
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

from components.layout import (
    setup_page, section, plotly_config,
    _AMBER, _CYAN, _GREEN, _RED, _TEXT_SEC, _TEXT_MUT,
)
from core.state import bootstrap
from core.context import load_context
from signals.momentum import momentum_signal
from signals.composite import rank_signal
from core.strategy import LowVolatilityStrategy

setup_page(
    "Live Signal Dashboard",
    "Current factor ranks and long/short signals for your universe — updated from Yahoo Finance.",
    "📡",
)
bootstrap()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ Universe")

    PRESETS = {
        "Large Cap (10)": [
            "AAPL", "MSFT", "AMZN", "GOOGL", "META",
            "NVDA", "TSLA", "JPM", "V", "UNH",
        ],
        "S&P 500 Leaders (15)": [
            "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA",
            "BRK-B", "UNH", "JPM", "V", "XOM", "JNJ", "PG", "HD",
        ],
        "Tech Focus": [
            "AAPL", "MSFT", "NVDA", "GOOGL", "META",
            "AMD", "INTC", "CRM", "ORCL", "ADBE",
            "QCOM", "TSLA", "NFLX", "AMZN", "PYPL",
        ],
        "Custom": [],
    }

    preset = st.selectbox("Universe Preset", list(PRESETS.keys()))
    if preset == "Custom":
        raw = st.text_area("Tickers (one per line)", value="AAPL\nMSFT\nNVDA\nGOOGL\nMETA")
        tickers = [t.strip().upper() for t in raw.splitlines() if t.strip()]
    else:
        tickers = PRESETS[preset]

    st.divider()
    lookback_days = st.slider("Price Lookback (days)", 60, 504, 252)
    long_q  = st.slider("Long threshold (top %)",    50, 90, 70) / 100
    short_q = st.slider("Short threshold (bottom %)", 10, 50, 30) / 100

    st.divider()
    include_lowvol = st.checkbox("Include Low-Vol signal", value=False)

# ── Context banner ────────────────────────────────────────────────────────────
ctx = load_context()
if ctx and ctx.is_complete():
    st.info(
        f"💾 StrategyContext available: **{ctx.strategy_name}** "
        f"({ctx.start_date} → {ctx.end_date}) · "
        f"Tickers: {', '.join(ctx.tickers[:5])}{'…' if len(ctx.tickers) > 5 else ''}",
        icon="ℹ️",
    )

if not tickers:
    st.warning("Select or enter at least one ticker.")
    st.stop()

# ── Download current prices ───────────────────────────────────────────────────
section("Live Market Data", f"Downloading {len(tickers)} tickers from Yahoo Finance.")

start_date = (datetime.today() - timedelta(days=lookback_days + 60)).strftime("%Y-%m-%d")

with st.spinner(f"Fetching {len(tickers)} tickers…"):
    raw = yf.download(tickers, start=start_date, auto_adjust=True, progress=False)

if raw is None or raw.empty:
    st.error("No data returned from Yahoo Finance. Check your internet connection.")
    st.stop()

if isinstance(raw.columns, pd.MultiIndex):
    prices = raw["Close"]
else:
    prices = raw[["Close"]].rename(columns={"Close": tickers[0]}) if len(tickers) == 1 else raw

prices = prices.dropna(how="all").ffill()
prices = prices[[c for c in prices.columns if prices[c].notna().sum() > 30]]

last_date  = prices.index[-1].date()
n_days     = len(prices)
n_tickers  = len(prices.columns)

d1, d2, d3, d4 = st.columns(4)
d1.metric("Last Price Date",  str(last_date))
d2.metric("Trading Days",     str(n_days))
d3.metric("Tickers",          str(n_tickers))
d4.metric("Signal",           "Momentum (12-1)")

# ── Compute signals ───────────────────────────────────────────────────────────
section("Factor Scores & Rankings", "Cross-sectional momentum rank — 100% = strongest, 0% = weakest.")

price_returns = prices.pct_change()

mom        = momentum_signal(prices)
mom_rank   = rank_signal(mom)

signals_to_avg = [mom_rank]
signal_labels  = ["Momentum"]

if include_lowvol:
    lv_strat  = LowVolatilityStrategy(window=20)
    lv_signal = lv_strat.generate_signal(prices)
    lv_rank   = rank_signal(lv_signal)
    signals_to_avg.append(lv_rank)
    signal_labels.append("Low Vol")

# Composite rank (mean of selected signals)
composite_rank = sum(signals_to_avg) / len(signals_to_avg)

today_rank     = composite_rank.iloc[-1].dropna().sort_values(ascending=False)
yesterday_rank = composite_rank.iloc[-2].dropna() if len(composite_rank) > 1 else today_rank

def classify(rank: float) -> str:
    if rank >= long_q:   return "LONG"
    if rank <= short_q:  return "SHORT"
    return "HOLD"

signal_df = pd.DataFrame({
    "Ticker":  today_rank.index,
    "Rank %":  (today_rank.values * 100).round(1),
    "Signal":  [classify(r) for r in today_rank.values],
    "Δ Rank":  [
        round((today_rank.get(t, 0) - yesterday_rank.get(t, 0)) * 100, 1)
        for t in today_rank.index
    ],
}).reset_index(drop=True)

# Latest prices
latest_px = prices.iloc[-1]
prev_px   = prices.iloc[-2] if len(prices) > 1 else prices.iloc[-1]
signal_df["Last Price"] = signal_df["Ticker"].map(lambda t: round(float(latest_px.get(t, np.nan)), 2))
signal_df["1d Ret %"]   = signal_df["Ticker"].map(
    lambda t: round((float(latest_px.get(t, 1)) / float(prev_px.get(t, 1)) - 1) * 100, 2)
    if prev_px.get(t, 0) != 0 else 0.0
)

# ── Summary metrics ───────────────────────────────────────────────────────────
n_long  = int((signal_df["Signal"] == "LONG").sum())
n_short = int((signal_df["Signal"] == "SHORT").sum())
n_hold  = int((signal_df["Signal"] == "HOLD").sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("▲ LONG",  str(n_long),  delta=None)
m2.metric("▼ SHORT", str(n_short), delta=None)
m3.metric("● HOLD",  str(n_hold),  delta=None)
m4.metric("Signal(s)", " + ".join(signal_labels))

# ── Signal table ──────────────────────────────────────────────────────────────
def _color_signal(val: str) -> str:
    if val == "LONG":  return f"color: {_GREEN}; font-weight:700"
    if val == "SHORT": return f"color: {_RED};   font-weight:700"
    return f"color: {_TEXT_MUT}"

def _color_ret(val: float) -> str:
    if val > 0:  return f"color: {_GREEN}"
    if val < 0:  return f"color: {_RED}"
    return ""

st.dataframe(
    signal_df.style
        .applymap(_color_signal, subset=["Signal"])
        .applymap(_color_ret, subset=["1d Ret %", "Δ Rank"])
        .format({
            "Rank %":     "{:.1f}",
            "Δ Rank":     "{:+.1f}",
            "Last Price": "{:.2f}",
            "1d Ret %":   "{:+.2f}%",
        }),
    use_container_width=True,
    height=420,
)

st.divider()

# ── Rank bar chart ────────────────────────────────────────────────────────────
section("Current Rank Distribution", "Green = LONG, Red = SHORT, Grey = HOLD.")

bar_colors = [
    _GREEN if r >= long_q else (_RED if r <= short_q else "#475569")
    for r in today_rank.values
]
fig_bar = go.Figure(go.Bar(
    x=list(today_rank.index),
    y=(today_rank.values * 100).tolist(),
    marker_color=bar_colors,
    text=[f"{v:.1f}%" for v in today_rank.values * 100],
    textposition="outside",
))
fig_bar.add_hline(y=long_q  * 100, line_dash="dot", line_color=_GREEN,
                  annotation_text="LONG threshold", annotation_font_color=_GREEN)
fig_bar.add_hline(y=short_q * 100, line_dash="dot", line_color=_RED,
                  annotation_text="SHORT threshold", annotation_font_color=_RED)
fig_bar.update_layout(
    title=f"Composite Rank as of {last_date}",
    xaxis_title="Ticker", yaxis_title="Rank (%)",
    yaxis=dict(range=[0, 105]),
    **plotly_config(),
)
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ── Rolling rank heatmap ──────────────────────────────────────────────────────
section(
    "60-Day Rolling Rank Heatmap",
    "Darker green = stronger momentum signal. Watch for regime flips.",
)

n_hm   = min(60, len(composite_rank))
hm_dat = composite_rank.iloc[-n_hm:][today_rank.index]

fig_hm = go.Figure(go.Heatmap(
    z=(hm_dat.values.T * 100),
    x=[str(d.date()) for d in hm_dat.index],
    y=list(hm_dat.columns),
    colorscale=[[0.0, _RED], [0.5, "#1e293b"], [1.0, _GREEN]],
    zmid=50,
    colorbar=dict(title="Rank %", ticksuffix="%"),
    hoverongaps=False,
))
fig_hm.update_layout(
    title=f"Rolling Momentum Rank — last {n_hm} trading days",
    xaxis_title="Date",
    yaxis_title="Ticker",
    height=max(300, n_tickers * 28),
    **plotly_config(),
)
fig_hm.update_xaxes(tickangle=45, nticks=12)
st.plotly_chart(fig_hm, use_container_width=True)

st.divider()

# ── Signal movers ─────────────────────────────────────────────────────────────
section("Signal Movers", "Tickers with the largest rank change since yesterday.")

movers = signal_df.reindex(signal_df["Δ Rank"].abs().sort_values(ascending=False).index)

fig_mv = go.Figure(go.Bar(
    x=movers["Ticker"].tolist(),
    y=movers["Δ Rank"].tolist(),
    marker_color=[_GREEN if v > 0 else _RED for v in movers["Δ Rank"]],
    text=[f"{v:+.1f}" for v in movers["Δ Rank"]],
    textposition="outside",
))
fig_mv.add_hline(y=0, line_color="#334155")
fig_mv.update_layout(
    title="Rank Change vs Yesterday (percentage points)",
    xaxis_title="Ticker",
    yaxis_title="Δ Rank (pp)",
    **plotly_config(),
)
st.plotly_chart(fig_mv, use_container_width=True)

st.divider()

# ── Momentum path for selected ticker ─────────────────────────────────────────
section("Ticker Deep-Dive", "Inspect the momentum rank history and price path for any ticker.")

if n_tickers > 0:
    selected = st.selectbox("Select ticker", list(today_rank.index))
    if selected in mom_rank.columns:
        c1, c2 = st.columns(2)

        with c1:
            fig_px = go.Figure(go.Scatter(
                x=prices.index, y=prices[selected],
                mode="lines", name=selected,
                line=dict(color=_CYAN, width=2),
            ))
            fig_px.update_layout(
                title=f"{selected} — Adjusted Close",
                xaxis_title="Date", yaxis_title="Price (USD)",
                **plotly_config(),
            )
            st.plotly_chart(fig_px, use_container_width=True)

        with c2:
            rank_ts = mom_rank[selected].dropna()
            fig_rk = go.Figure()
            fig_rk.add_trace(go.Scatter(
                x=rank_ts.index, y=rank_ts.values * 100,
                mode="lines", name="Momentum Rank %",
                line=dict(color=_AMBER, width=2),
            ))
            fig_rk.add_hline(y=long_q  * 100, line_dash="dot", line_color=_GREEN)
            fig_rk.add_hline(y=short_q * 100, line_dash="dot", line_color=_RED)
            fig_rk.add_hrect(
                y0=long_q * 100, y1=100,
                fillcolor=_GREEN, opacity=0.05, line_width=0,
            )
            fig_rk.add_hrect(
                y0=0, y1=short_q * 100,
                fillcolor=_RED, opacity=0.05, line_width=0,
            )
            fig_rk.update_layout(
                title=f"{selected} — Momentum Rank %",
                xaxis_title="Date", yaxis_title="Rank (%)",
                yaxis=dict(range=[0, 100]),
                **plotly_config(),
            )
            st.plotly_chart(fig_rk, use_container_width=True)
