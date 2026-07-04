import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

from components.layout import setup_page, section, next_step, plotly_config, _GREEN, _RED, _AMBER, _CYAN, _TEXT_MUT
from data.universe import get_universe
from market.prices import fetch_latest_prices

setup_page(
    "Market Prices",
    "Live prices, sparklines, and market breadth across major US equity universes.",
    "📈"
)

# ── Sidebar controls ──────────────────────────────────────────────────────────
st.sidebar.header("Universe")
universe_name = st.sidebar.selectbox("Index", ["S&P 500", "Nasdaq 100", "Dow 30"], index=0)
max_tickers   = st.sidebar.slider("Max tickers", 10, 200, 50, step=10)
sort_by       = st.sidebar.selectbox("Sort by", ["% Change ↓", "% Change ↑", "Price ↓", "Price ↑", "Ticker A-Z"])

if st.sidebar.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()
st.sidebar.header("Single Ticker")
single_ticker = st.sidebar.text_input("Lookup", placeholder="e.g. AAPL")


# ── Cached fetchers ───────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def _load_prices(tickers):
    return fetch_latest_prices(tickers, period="5d", interval="1d")


@st.cache_data(ttl=300)
def _load_sparklines(tickers):
    """Fetch 5-day daily closes for sparkline rendering."""
    try:
        raw = yf.download(tickers, period="5d", interval="1d",
                          auto_adjust=True, progress=False)
        if raw.empty:
            return {}
        closes = raw["Close"]
        if isinstance(closes, pd.Series):
            closes = closes.to_frame(name=tickers[0] if len(tickers)==1 else "unknown")
        result = {}
        for col in closes.columns:
            vals = closes[col].dropna().tolist()
            if len(vals) >= 2:
                result[str(col)] = vals
        return result
    except Exception:
        return {}


@st.cache_data(ttl=3600)
def _load_detail_chart(ticker):
    try:
        return yf.download(ticker, period="3mo", interval="1d",
                           auto_adjust=True, progress=False)
    except Exception:
        return pd.DataFrame()


# ── SVG sparkline helper ──────────────────────────────────────────────────────

def _svg_spark(closes, positive=True, w=88, h=34):
    if len(closes) < 2:
        return ""
    mn, mx = min(closes), max(closes)
    rng = mx - mn or 1
    color = _GREEN if positive else _RED
    pts = []
    for i, v in enumerate(closes):
        x = i / (len(closes) - 1) * w
        y = h - ((v - mn) / rng) * (h - 4) - 2
        pts.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(pts)
    # Fill area under line
    fill_pts = f"0,{h} " + polyline + f" {w},{h}"
    fill_color = f"rgba(16,185,129,0.10)" if positive else f"rgba(239,68,68,0.10)"
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'style="display:block;overflow:visible;">'
        f'<polygon points="{fill_pts}" fill="{fill_color}"/>'
        f'<polyline points="{polyline}" fill="none" stroke="{color}" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )


# ── Load data ─────────────────────────────────────────────────────────────────

tickers = get_universe(universe_name)[:max_tickers]
prices_df = _load_prices(tickers)
sparks    = _load_sparklines(tickers)

if prices_df is None or prices_df.empty:
    st.warning("Could not load price data. Try refreshing.")
    st.stop()

# Ensure tickers are always in a column named "ticker"
if "ticker" not in prices_df.columns:
    prices_df.index.name = "ticker"
    prices_df = prices_df.reset_index()

# Apply sort
_sort_map = {
    "% Change ↓": ("pct_change", False),
    "% Change ↑": ("pct_change", True),
    "Price ↓":    ("price", False),
    "Price ↑":    ("price", True),
    "Ticker A-Z": ("ticker", True),
}
_scol, _sasc = _sort_map[sort_by]
prices_df = prices_df.sort_values(_scol, ascending=_sasc).reset_index(drop=True)


# ── Search filter ─────────────────────────────────────────────────────────────

search = st.text_input("", placeholder="🔍  Search ticker or filter list…",
                       label_visibility="collapsed")
if search.strip():
    _q = search.strip().upper()
    prices_df = prices_df[prices_df["ticker"].str.upper().str.contains(_q, na=False)]

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ── Summary bar ───────────────────────────────────────────────────────────────

_adv = int((prices_df["pct_change"] > 0).sum())
_dec = int((prices_df["pct_change"] < 0).sum())
_unch = len(prices_df) - _adv - _dec
_avg  = float(prices_df["pct_change"].mean())

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Loaded",     f"{len(prices_df)}")
m2.metric("▲ Advancing", str(_adv),  delta=None)
m3.metric("▼ Declining", str(_dec),  delta=None)
m4.metric("Avg Move",   f"{_avg:+.2f}%")
m5.metric("Unchanged",  str(_unch))

st.divider()


# ── Robinhood-style card grid ─────────────────────────────────────────────────

st.markdown(
    f'<p style="font-family:\'JetBrains Mono\',monospace;font-size:0.58rem;'
    f'font-weight:800;color:rgba(245,158,11,0.5);text-transform:uppercase;'
    f'letter-spacing:0.18em;margin-bottom:12px;">{universe_name} · {len(prices_df)} stocks</p>',
    unsafe_allow_html=True,
)

# CSS for cards
st.markdown("""
<style>
.rb-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: 10px;
    margin-bottom: 24px;
}
.rb-card {
    background: linear-gradient(145deg, rgba(13,20,33,0.95), rgba(10,16,28,0.90));
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 14px 14px 10px;
    position: relative;
    transition: transform 0.14s ease, border-color 0.14s ease;
    cursor: default;
}
.rb-card:hover {
    transform: translateY(-2px);
    border-color: rgba(245,158,11,0.25);
}
.rb-ticker {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.80rem;
    font-weight: 700;
    color: #E2E8F0;
    letter-spacing: 0.04em;
}
.rb-price {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.05rem;
    font-weight: 700;
    color: #F1F5F9;
    margin: 4px 0 2px;
    letter-spacing: -0.01em;
}
.rb-change-pos {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    color: #10B981;
}
.rb-change-neg {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    color: #EF4444;
}
.rb-change-neu {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    color: #475569;
}
.rb-spark { margin-top: 8px; }
</style>
""", unsafe_allow_html=True)

# Build card HTML
cards_html = '<div class="rb-grid">'

for _, row in prices_df.iterrows():
    tkr   = str(row["ticker"])
    price = float(row["price"])
    pct   = float(row["pct_change"])
    pos   = pct >= 0

    price_str = f"${price:,.2f}" if price < 1000 else f"${price:,.0f}"
    pct_str   = f"{'▲' if pos else '▼'} {abs(pct):.2f}%"
    chg_cls   = "rb-change-pos" if pos else ("rb-change-neg" if pct < 0 else "rb-change-neu")

    spark_data = sparks.get(tkr, [])
    spark_svg  = _svg_spark(spark_data, positive=pos) if spark_data else ""

    cards_html += f"""
    <div class="rb-card">
        <div class="rb-ticker">{tkr}</div>
        <div class="rb-price">{price_str}</div>
        <div class="{chg_cls}">{pct_str}</div>
        <div class="rb-spark">{spark_svg}</div>
    </div>"""

cards_html += "</div>"
st.markdown(cards_html, unsafe_allow_html=True)


# ── Top movers ────────────────────────────────────────────────────────────────

st.divider()
g_col, l_col = st.columns(2)

with g_col:
    section("Top Gainers")
    _top = prices_df.sort_values("pct_change", ascending=False).head(10)
    for _, r in _top.iterrows():
        tkr = str(r["ticker"])
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.78rem;'
            f'font-weight:700;color:#E2E8F0;">{tkr}</span>'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.76rem;'
            f'color:#10B981;font-weight:600;">+{r["pct_change"]:.2f}%&nbsp;&nbsp;'
            f'${r["price"]:,.2f}</span></div>',
            unsafe_allow_html=True,
        )

with l_col:
    section("Top Losers")
    _bot = prices_df.sort_values("pct_change").head(10)
    for _, r in _bot.iterrows():
        tkr = str(r["ticker"])
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.78rem;'
            f'font-weight:700;color:#E2E8F0;">{tkr}</span>'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.76rem;'
            f'color:#EF4444;font-weight:600;">{r["pct_change"]:.2f}%&nbsp;&nbsp;'
            f'${r["price"]:,.2f}</span></div>',
            unsafe_allow_html=True,
        )


# ── Single ticker detail ──────────────────────────────────────────────────────

if single_ticker.strip():
    st.divider()
    _t = single_ticker.strip().upper()
    section(f"{_t} — 3-Month Chart")

    _detail = _load_detail_chart(_t)
    if _detail.empty:
        st.error(f"No data found for {_t}.")
    else:
        _close = _detail["Close"].squeeze().dropna()
        _pos   = float(_close.iloc[-1]) >= float(_close.iloc[0])
        _color = _GREEN if _pos else _RED
        _fill  = "rgba(16,185,129,0.08)" if _pos else "rgba(239,68,68,0.08)"

        fig = go.Figure(go.Scatter(
            x=_close.index, y=_close.values,
            mode="lines", name=_t,
            line=dict(color=_color, width=2),
            fill="tozeroy", fillcolor=_fill,
        ))
        fig.update_layout(
            title=f"{_t} — 3-Month Daily Close",
            xaxis_title="Date", yaxis_title="Price (USD)",
            **plotly_config(height=380),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Quick stats
        _ret  = (_close.iloc[-1] / _close.iloc[0] - 1) * 100
        _high = float(_close.max())
        _low  = float(_close.min())
        _vol  = float(_close.pct_change().std() * (252**0.5) * 100)
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Current",   f"${float(_close.iloc[-1]):,.2f}")
        s2.metric("3M Return", f"{_ret:+.2f}%")
        s3.metric("52W High",  f"${_high:,.2f}")
        s4.metric("Ann. Vol",  f"{_vol:.1f}%")


next_step("Use Market Anomalies or Daily Picks to turn price movements into trading signals.")
