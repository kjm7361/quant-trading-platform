"""
22_Factor_Research.py  ·  Multi-Factor Equity Research Engine
Factors: Momentum · Value · Quality · Profitability · Low-Vol · Composite
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

from components.layout import (
    setup_page, section, next_step, plotly_config,
    _AMBER, _CYAN, _GREEN, _RED, _TEXT_SEC, _TEXT_MUT,
)
from core.state import bootstrap, set_factor_scores, set_signal

# ── Page init ─────────────────────────────────────────────────────────────────
setup_page(
    "Factor Research Engine",
    "Multi-factor equity scoring: Momentum · Value · Quality · Profitability · Low-Vol",
    "🔬",
)
bootstrap()

# ── Default universe ──────────────────────────────────────────────────────────
_DEFAULT_30 = [
    "AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","BRK-B",
    "UNH","JPM","JNJ","V","XOM","PG","MA","HD",
    "AVGO","MRK","PEP","ABBV","COST","LLY","MCD","BAC",
    "WMT","DIS","NFLX","ADBE","CRM","AMD",
]
_MAG7 = ["AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA"]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ Factor Research")
    universe_choice = st.selectbox(
        "Universe", ["Default 30 Stocks", "Magnificent 7", "Custom Tickers"],
        key="fr_uni",
    )
    if universe_choice == "Custom Tickers":
        raw = st.text_area(
            "Tickers (comma-separated)",
            value="AAPL, MSFT, GOOGL, TSLA, NVDA, AMD, META",
            key="fr_custom",
        )
        tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]
    elif universe_choice == "Magnificent 7":
        tickers = _MAG7
    else:
        tickers = _DEFAULT_30

    lookback = st.slider("Lookback (years)", 1, 3, 2, key="fr_lb")
    st.markdown("---")
    st.markdown("**Factor Weights**")
    w_mom  = st.slider("Momentum",      0, 5, 1, key="fr_wmom")
    w_val  = st.slider("Value",         0, 5, 1, key="fr_wval")
    w_qual = st.slider("Quality (ROE)", 0, 5, 1, key="fr_wqual")
    w_prof = st.slider("Profitability", 0, 5, 1, key="fr_wprof")
    w_lvol = st.slider("Low-Vol",       0, 5, 1, key="fr_wlvol")
    run_btn = st.button("▶ Run Factor Analysis", type="primary", use_container_width=True)

# ── Data loaders ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _load_prices(tickers_key: str, years: int) -> pd.DataFrame:
    tickers = list(tickers_key.split("|"))
    end   = datetime.today()
    start = end - timedelta(days=365 * years + 60)
    try:
        raw = yf.download(
            tickers, start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            auto_adjust=True, progress=False,
        )
        if raw.empty:
            return pd.DataFrame()
        if isinstance(raw.columns, pd.MultiIndex):
            closes = raw["Close"] if "Close" in raw.columns.get_level_values(0) else pd.DataFrame()
        else:
            closes = raw[["Close"]].rename(columns={"Close": tickers[0]}) if "Close" in raw.columns else pd.DataFrame()
        return closes.ffill().dropna(how="all")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=7200, show_spinner=False)
def _load_info(ticker: str) -> dict:
    try:
        info = yf.Ticker(ticker).info
        return {
            "priceToBook":    info.get("priceToBook"),
            "returnOnEquity": info.get("returnOnEquity"),
            "grossMargins":   info.get("grossMargins"),
            "trailingPE":     info.get("trailingPE"),
        }
    except Exception:
        return {}


# ── Factor computers ──────────────────────────────────────────────────────────
def _pct_rank(s: pd.Series) -> pd.Series:
    return s.rank(pct=True)


def _momentum(prices: pd.DataFrame) -> pd.Series:
    """12-1 month momentum."""
    n = len(prices)
    if n < 21:
        return pd.Series(0.0, index=prices.columns)
    skip1m  = prices.iloc[-21]
    start   = prices.iloc[-min(252, n)]
    latest  = prices.iloc[-1]
    mom     = (latest / skip1m) * (skip1m / start) - 1
    return mom.replace([np.inf, -np.inf], np.nan).fillna(0)


def _low_vol(prices: pd.DataFrame) -> pd.Series:
    ret = prices.pct_change().dropna()
    vol = ret.tail(min(252, len(ret))).std() * np.sqrt(252)
    return (-vol).replace([np.inf, -np.inf], np.nan).fillna(0)


def _value(prices: pd.DataFrame, info_map: dict) -> tuple[pd.Series, dict]:
    rows, sources = {}, {}
    for t in prices.columns:
        inf = info_map.get(t, {})
        pb  = inf.get("priceToBook")
        pe  = inf.get("trailingPE")
        if pb and pb > 0:
            rows[t] = 1.0 / pb
            sources[t] = "P/B"
        elif pe and pe > 0:
            rows[t] = 1.0 / pe
            sources[t] = "1/PE ✦"
        else:
            n = len(prices)
            rows[t] = -(prices[t].iloc[-1] / prices[t].iloc[-min(252, n)] - 1)
            sources[t] = "Reversal ✦"
    return pd.Series(rows).replace([np.inf, -np.inf], np.nan).fillna(0), sources


def _quality(prices: pd.DataFrame, info_map: dict) -> tuple[pd.Series, dict]:
    rows, sources = {}, {}
    for t in prices.columns:
        roe = info_map.get(t, {}).get("returnOnEquity")
        if roe is not None:
            rows[t] = float(roe)
            sources[t] = "ROE"
        else:
            ret = prices[t].pct_change().dropna()
            rows[t] = float(ret.mean() / (ret.std() + 1e-9) * np.sqrt(252))
            sources[t] = "Sharpe ✦"
    return pd.Series(rows).replace([np.inf, -np.inf], np.nan).fillna(0), sources


def _profitability(prices: pd.DataFrame, info_map: dict) -> tuple[pd.Series, dict]:
    rows, sources = {}, {}
    for t in prices.columns:
        gm = info_map.get(t, {}).get("grossMargins")
        if gm is not None:
            rows[t] = float(gm)
            sources[t] = "Gross Margin"
        else:
            n     = len(prices)
            r12   = prices[t].iloc[-1] / prices[t].iloc[-min(252, n)] - 1
            vol   = prices[t].pct_change().dropna().std() * np.sqrt(252) + 1e-9
            rows[t] = float(r12 / vol)
            sources[t] = "Ret/Vol ✦"
    return pd.Series(rows).replace([np.inf, -np.inf], np.nan).fillna(0), sources


def _composite(mom_r, val_r, qual_r, prof_r, lvol_r, wm, wv, wq, wp, wl) -> pd.Series:
    w = wm + wv + wq + wp + wl + 1e-9
    return (mom_r*wm + val_r*wv + qual_r*wq + prof_r*wp + lvol_r*wl) / w


# ── Placeholder before first run ──────────────────────────────────────────────
if not run_btn and "fr_results" not in st.session_state:
    st.markdown(
        f"""<div style="background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.18);
        border-left:4px solid {_AMBER};border-radius:8px;padding:20px 24px;
        font-family:Inter,sans-serif;color:{_TEXT_SEC};line-height:1.7;">
        <b style="color:{_AMBER};">How to use this module</b><br>
        1. Select a stock universe and lookback in the sidebar.<br>
        2. Adjust factor weights (0 = ignore that factor, 5 = max weight).<br>
        3. Press <b>▶ Run Factor Analysis</b>.<br><br>
        Factors marked <span style="color:{_CYAN};">✦</span> use price-based proxies
        when Yahoo Finance fundamental data is unavailable.
        </div>""",
        unsafe_allow_html=True,
    )
    st.stop()

# ── Run pipeline ──────────────────────────────────────────────────────────────
if run_btn:
    tickers_key = "|".join(sorted(set(tickers)))

    with st.spinner(f"Downloading {len(tickers)} stocks — {lookback}yr history…"):
        prices = _load_prices(tickers_key, lookback)

    if prices.empty:
        st.error("No price data returned. Check ticker symbols and try again.")
        st.stop()

    available = [t for t in tickers if t in prices.columns]
    if not available:
        st.error("None of the requested tickers returned valid data.")
        st.stop()

    prices = prices[available].dropna(how="all")

    prog = st.progress(0, text="Fetching fundamentals…")
    info_map: dict = {}
    for i, t in enumerate(available):
        info_map[t] = _load_info(t)
        prog.progress((i + 1) / len(available), text=f"Fetching {t}…")
    prog.empty()

    # Compute raw factors
    mom_raw  = _momentum(prices)
    lvol_raw = _low_vol(prices)
    val_raw,  val_src  = _value(prices, info_map)
    qual_raw, qual_src = _quality(prices, info_map)
    prof_raw, prof_src = _profitability(prices, info_map)

    # Align tickers
    common = list(
        set(mom_raw.index) & set(lvol_raw.index) &
        set(val_raw.index) & set(qual_raw.index) & set(prof_raw.index)
    )
    if not common:
        st.error("No common tickers across all factors. Try a different universe.")
        st.stop()

    mom_r  = _pct_rank(mom_raw[common])
    lvol_r = _pct_rank(lvol_raw[common])
    val_r  = _pct_rank(val_raw[common])
    qual_r = _pct_rank(qual_raw[common])
    prof_r = _pct_rank(prof_raw[common])
    comp_r = _composite(mom_r, val_r, qual_r, prof_r, lvol_r, w_mom, w_val, w_qual, w_prof, w_lvol)

    factor_df = pd.DataFrame({
        "Momentum":      mom_r[common].round(3),
        "Value":         val_r[common].round(3),
        "Quality":       qual_r[common].round(3),
        "Profitability": prof_r[common].round(3),
        "Low-Vol":       lvol_r[common].round(3),
        "Composite":     comp_r[common].round(3),
    }).sort_values("Composite", ascending=False)

    # Persist to shared state
    set_factor_scores({t: dict(factor_df.loc[t]) for t in factor_df.index})
    top5 = list(factor_df.index[:5])
    bot5 = list(factor_df.index[-5:])
    for t in top5:
        set_signal(t, "BUY",  float(factor_df.loc[t, "Composite"]), "Factor")
    for t in bot5:
        set_signal(t, "SELL", 1.0 - float(factor_df.loc[t, "Composite"]), "Factor")

    st.session_state["fr_results"] = {
        "factor_df": factor_df,
        "info_map":  info_map,
        "val_src":   val_src,
        "qual_src":  qual_src,
        "prof_src":  prof_src,
        "prices":    prices,
    }
    st.success(f"✓ Factor analysis complete — {len(common)} stocks ranked.")

# ── Results ───────────────────────────────────────────────────────────────────
if "fr_results" not in st.session_state:
    st.stop()

res       = st.session_state["fr_results"]
factor_df = res["factor_df"]
n         = len(factor_df)

# ── Summary ───────────────────────────────────────────────────────────────────
section("Factor Analysis Summary")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Stocks Ranked",       n)
m2.metric("Top Score",           f"{factor_df['Composite'].max():.3f}")
m3.metric("Bottom Score",        f"{factor_df['Composite'].min():.3f}")
m4.metric("Mean Score",          f"{factor_df['Composite'].mean():.3f}")
m5.metric("Score Dispersion",    f"{factor_df['Composite'].std():.3f}")

# ── Full ranking table ────────────────────────────────────────────────────────
section("📊 Factor Rankings", "All stocks ranked by composite score (0 = weak · 1 = strong)")

def _cell_color(val):
    if   val >= 0.70: return "color:#10B981;font-weight:700"
    elif val >= 0.50: return "color:#F59E0B"
    elif val <= 0.30: return "color:#EF4444"
    return "color:#94A3B8"

styled = (
    factor_df
    .style
    .applymap(_cell_color, subset=list(factor_df.columns))
    .format("{:.3f}")
)
st.dataframe(styled, use_container_width=True, height=440)

# Export
csv_bytes = factor_df.to_csv().encode()
st.download_button(
    "⬇ Download Rankings CSV",
    data=csv_bytes,
    file_name=f"factor_rankings_{datetime.today().strftime('%Y%m%d')}.csv",
    mime="text/csv",
)

# ── Long / Short candidates ───────────────────────────────────────────────────
section("Long / Short Candidates")
top_n = min(8, max(1, n // 3))
col_l, col_r = st.columns(2)

with col_l:
    st.markdown(
        f"<div style='font-family:JetBrains Mono,monospace;font-size:0.65rem;"
        f"font-weight:800;color:{_GREEN};text-transform:uppercase;letter-spacing:0.14em;"
        f"margin-bottom:10px;'>🟢 Top Long Candidates</div>",
        unsafe_allow_html=True,
    )
    for rank, (t, row) in enumerate(factor_df.head(top_n).iterrows(), 1):
        score = row["Composite"]
        pct   = int(score * 100)
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:10px;padding:9px 12px;
            margin-bottom:5px;border-radius:6px;
            background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.18);">
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;
                color:{_TEXT_MUT};width:22px;">#{rank}</span>
            <span style="font-family:'JetBrains Mono',monospace;font-weight:700;
                color:#E2E8F0;flex:1;">{t}</span>
            <div style="background:rgba(16,185,129,0.15);border-radius:4px;
                height:6px;width:60px;overflow:hidden;">
                <div style="background:{_GREEN};height:100%;width:{pct}%;border-radius:4px;"></div>
            </div>
            <span style="font-family:'JetBrains Mono',monospace;color:{_GREEN};
                font-weight:700;font-size:0.88rem;width:42px;text-align:right;">{score:.3f}</span>
            <span style="font-size:0.60rem;color:{_GREEN};background:rgba(16,185,129,0.14);
                padding:2px 7px;border-radius:999px;font-family:'JetBrains Mono',monospace;">LONG</span>
            </div>""",
            unsafe_allow_html=True,
        )

with col_r:
    st.markdown(
        f"<div style='font-family:JetBrains Mono,monospace;font-size:0.65rem;"
        f"font-weight:800;color:{_RED};text-transform:uppercase;letter-spacing:0.14em;"
        f"margin-bottom:10px;'>🔴 Weak / Short Candidates</div>",
        unsafe_allow_html=True,
    )
    for rank, (t, row) in enumerate(factor_df.tail(top_n).iloc[::-1].iterrows(), 1):
        score = row["Composite"]
        pct   = int((1 - score) * 100)
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:10px;padding:9px 12px;
            margin-bottom:5px;border-radius:6px;
            background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.18);">
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;
                color:{_TEXT_MUT};width:22px;">#{rank}</span>
            <span style="font-family:'JetBrains Mono',monospace;font-weight:700;
                color:#E2E8F0;flex:1;">{t}</span>
            <div style="background:rgba(239,68,68,0.15);border-radius:4px;
                height:6px;width:60px;overflow:hidden;">
                <div style="background:{_RED};height:100%;width:{pct}%;border-radius:4px;"></div>
            </div>
            <span style="font-family:'JetBrains Mono',monospace;color:{_RED};
                font-weight:700;font-size:0.88rem;width:42px;text-align:right;">{score:.3f}</span>
            <span style="font-size:0.60rem;color:{_RED};background:rgba(239,68,68,0.14);
                padding:2px 7px;border-radius:999px;font-family:'JetBrains Mono',monospace;">SHORT</span>
            </div>""",
            unsafe_allow_html=True,
        )

# ── Factor heatmap ────────────────────────────────────────────────────────────
section("Factor Heatmap", "Cross-sectional factor exposures — percentile rank [0=weak, 1=strong]")

display_tickers = factor_df.index[:24].tolist()
heat_vals = factor_df.loc[display_tickers, ["Momentum","Value","Quality","Profitability","Low-Vol"]].T

fig_heat = go.Figure(go.Heatmap(
    z=heat_vals.values,
    x=display_tickers,
    y=heat_vals.index.tolist(),
    colorscale="RdYlGn",
    zmin=0, zmax=1,
    text=heat_vals.values.round(2),
    texttemplate="%{text}",
    textfont={"size": 8, "family": "JetBrains Mono, monospace"},
    showscale=True,
    colorbar=dict(
        thickness=10, len=0.8,
        tickfont=dict(family="JetBrains Mono", size=9, color="#94A3B8"),
    ),
))
fig_heat.update_layout(
    **plotly_config(
        height=290, margin=dict(l=95, r=20, t=10, b=90),
        xaxis=dict(tickfont=dict(family="JetBrains Mono", size=8), tickangle=-55),
        yaxis=dict(tickfont=dict(family="JetBrains Mono", size=10)),
    ),
)
st.plotly_chart(fig_heat, use_container_width=True)

# ── Factor exposure bar ───────────────────────────────────────────────────────
section("Average Factor Exposure", "Mean percentile rank across the universe for each factor")

avg_exp = factor_df[["Momentum","Value","Quality","Profitability","Low-Vol"]].mean()
bar_clrs = [_GREEN, _CYAN, _AMBER, "#8B5CF6", "#EC4899"]

fig_bar = go.Figure(go.Bar(
    x=avg_exp.index.tolist(),
    y=avg_exp.values.tolist(),
    marker=dict(color=bar_clrs, line=dict(width=0)),
    text=[f"{v:.3f}" for v in avg_exp.values],
    textposition="outside",
    textfont=dict(family="JetBrains Mono, monospace", size=10, color="#E2E8F0"),
))
fig_bar.add_hline(y=0.5, line_dash="dot", line_color="#475569",
                  annotation_text="Neutral 0.50", annotation_font_color="#475569")
fig_bar.update_layout(
    **plotly_config(
        height=310, margin=dict(l=0, r=0, t=20, b=40),
        yaxis=dict(range=[0, 1.18], title="Avg Rank"),
        xaxis=dict(tickfont=dict(family="JetBrains Mono", size=11)),
    ),
)
st.plotly_chart(fig_bar, use_container_width=True)

# ── Factor distribution ───────────────────────────────────────────────────────
section("Factor Score Distributions", "Histogram of composite scores across the universe")

fig_hist = go.Figure()
fig_hist.add_trace(go.Histogram(
    x=factor_df["Composite"].tolist(),
    nbinsx=20,
    marker_color=_AMBER,
    opacity=0.8,
    name="Composite",
))
fig_hist.add_vline(x=0.5, line_dash="dot", line_color=_CYAN,
                   annotation_text="Neutral", annotation_font_color=_CYAN)
fig_hist.update_layout(
    **plotly_config(height=260, margin=dict(l=0, r=0, t=10, b=40)),
    xaxis_title="Composite Score",
    yaxis_title="Count",
    bargap=0.05,
)
st.plotly_chart(fig_hist, use_container_width=True)

# ── Data source note ──────────────────────────────────────────────────────────
info_map  = res.get("info_map", {})
val_src   = res.get("val_src", {})
qual_src  = res.get("qual_src", {})
prof_src  = res.get("prof_src", {})
proxies   = [t for t in factor_df.index if "✦" in (val_src.get(t,"") + qual_src.get(t,"") + prof_src.get(t,""))]
if proxies:
    st.info(
        f"✦ Price-based proxies were used for {len(proxies)} stock(s) where Yahoo Finance "
        f"fundamental data was unavailable ({', '.join(proxies[:6])}{'…' if len(proxies)>6 else ''}). "
        f"Rankings remain valid but reflect market-implied rather than accounting-based fundamentals."
    )

next_step("Open ML Alpha Lab for machine-learning signal generation, or Portfolio Optimizer for sizing.")
