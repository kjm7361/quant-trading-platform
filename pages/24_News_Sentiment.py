"""
24_News_Sentiment.py  ·  News Sentiment Engine
Rule-based sentiment scoring from Google News RSS — no paid APIs required.
"""

import streamlit as st
import pandas as pd
import re
from datetime import datetime

try:
    import feedparser
    _FP_OK = True
except ImportError:
    _FP_OK = False

from components.layout import (
    setup_page, section, next_step, plotly_config,
    _AMBER, _CYAN, _GREEN, _RED, _TEXT_SEC, _TEXT_MUT,
)
from core.state import bootstrap, set_sentiment_scores, set_signal
import plotly.graph_objects as go

# ── Page init ─────────────────────────────────────────────────────────────────
setup_page(
    "News Sentiment Engine",
    "Rule-based market sentiment from Google News RSS — no paid APIs required",
    "📰",
)
bootstrap()

if not _FP_OK:
    st.error("feedparser is not installed. Run `pip install feedparser` and restart.", icon="⚠️")
    st.stop()

# ── Sentiment word lists ──────────────────────────────────────────────────────
_POSITIVE = {
    "surge","surges","surged","rally","rallies","rallied","beat","beats","exceeded",
    "record","profit","profits","growth","grew","grow","strong","stronger","strongest",
    "outperform","upgrade","upgraded","buy","bullish","bull","breakthrough","innovative",
    "revenue","earnings","gain","gains","rose","rises","rise","soar","soars","soared",
    "optimistic","positive","demand","recovery","recover","rebound","rebounded",
    "expansion","expand","expanded","dividend","dividends","acquisition","partner",
    "partnership","launch","launched","win","wins","won","success","successful",
    "momentum","accelerate","accelerated","above","upbeat","raised","raises",
}
_NEGATIVE = {
    "fall","falls","fell","drop","drops","dropped","decline","declines","declined",
    "loss","losses","miss","misses","missed","weak","weaker","weakest","cut","cuts",
    "cutting","downgrade","downgraded","sell","bearish","bear","concern","concerns",
    "risk","risks","warning","warn","warns","layoff","layoffs","shutdown","bankruptcy",
    "bankrupt","debt","default","investigation","lawsuit","fine","penalty","recall",
    "recall","slump","plunge","plunges","plunged","tumble","tumbles","tumbled",
    "worries","worry","disappointing","disappoint","below","downbeat","lowered",
    "lowers","fraud","dispute","regulatory","violation","crisis","trouble","troubled",
}
_INTENSIFIERS = {"very","highly","extremely","significantly","sharply","massively"}
_NEGATORS     = {"not","no","never","don't","doesn't","didn't","without","lack","lacks"}

# ── Scorer ────────────────────────────────────────────────────────────────────
def _score_text(text: str) -> float:
    words = re.findall(r"\b[a-z]+\b", text.lower())
    score, i = 0.0, 0
    while i < len(words):
        w = words[i]
        intensify = 1.6 if (i > 0 and words[i-1] in _INTENSIFIERS) else 1.0
        negate    = (i > 0 and words[i-1] in _NEGATORS)
        if w in _POSITIVE:
            score += (1.0 * intensify) * (-1.0 if negate else 1.0)
        elif w in _NEGATIVE:
            score -= (1.0 * intensify) * (-1.0 if negate else 1.0)
        i += 1
    return max(-5.0, min(5.0, score))


def _normalize(raw: float) -> float:
    """Map raw score in [-5,5] to [-1,1]."""
    return raw / 5.0


# ── RSS fetcher ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def _fetch_headlines(query: str, max_items: int = 50) -> list[dict]:
    q   = query.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    try:
        feed    = feedparser.parse(url)
        entries = feed.entries[:max_items]
        rows    = []
        for e in entries:
            title   = getattr(e, "title",   "")
            summary = getattr(e, "summary", "")
            pub     = getattr(e, "published", "")
            link    = getattr(e, "link",    "")
            raw     = _score_text(title + " " + summary)
            rows.append({
                "title":   title,
                "summary": summary[:220],
                "pub":     pub,
                "link":    link,
                "raw":     raw,
                "score":   _normalize(raw),
            })
        return rows
    except Exception:
        return []


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ News Sentiment")
    raw_tickers = st.text_area(
        "Tickers to monitor",
        value="AAPL, MSFT, GOOGL, NVDA, TSLA",
        key="ns_tickers",
    )
    tickers = [t.strip().upper() for t in raw_tickers.split(",") if t.strip()]
    extra_q  = st.text_input("Extra query terms (optional)", value="", key="ns_extra")
    max_items = st.slider("Max headlines per ticker", 10, 100, 40, key="ns_max")
    run_btn  = st.button("▶ Fetch & Score Headlines", type="primary", use_container_width=True)
    st.markdown("---")
    st.markdown(
        f"<span style='font-size:0.72rem;color:{_TEXT_MUT};'>Powered by Google News RSS — "
        f"no API key required.<br>Cache refreshes every 15 min.</span>",
        unsafe_allow_html=True,
    )

# ── Placeholder ───────────────────────────────────────────────────────────────
if not run_btn and "ns_results" not in st.session_state:
    st.markdown(
        f"""<div style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.18);
        border-left:4px solid {_GREEN};border-radius:8px;padding:20px 24px;
        font-family:Inter,sans-serif;color:{_TEXT_SEC};line-height:1.7;">
        <b style="color:{_GREEN};">How to use this module</b><br>
        1. Enter the tickers you want to monitor in the sidebar (comma-separated).<br>
        2. Optionally add extra search terms (e.g. "earnings Q2 2025").<br>
        3. Press <b>▶ Fetch & Score Headlines</b>.<br><br>
        Headlines are pulled from <b>Google News RSS</b> in real time — no API key needed.
        Sentiment is scored using a curated financial word list with intensifier and negation handling.
        </div>""",
        unsafe_allow_html=True,
    )
    st.stop()

# ── Fetch & score ─────────────────────────────────────────────────────────────
if run_btn:
    prog = st.progress(0, text="Fetching headlines…")
    all_headlines: list[dict] = []
    ticker_summaries: dict[str, dict] = {}

    for i, t in enumerate(tickers):
        query = f"{t} stock {extra_q}".strip()
        rows  = _fetch_headlines(query, max_items)
        for r in rows:
            r["ticker"] = t
        all_headlines.extend(rows)

        if rows:
            scores = [r["score"] for r in rows]
            avg    = float(pd.Series(scores).mean())
            pos    = sum(1 for s in scores if s > 0.1)
            neg    = sum(1 for s in scores if s < -0.1)
            neu    = len(scores) - pos - neg
            ticker_summaries[t] = {
                "avg_score": avg,
                "count":     len(rows),
                "positive":  pos,
                "negative":  neg,
                "neutral":   neu,
                "signal":    "BULLISH" if avg > 0.05 else ("BEARISH" if avg < -0.05 else "NEUTRAL"),
            }
        else:
            ticker_summaries[t] = {
                "avg_score": 0.0, "count": 0,
                "positive": 0, "negative": 0, "neutral": 0,
                "signal": "NEUTRAL",
            }

        prog.progress((i + 1) / len(tickers), text=f"Scored {t} — {len(rows)} headlines")

    prog.empty()

    # Write to shared state
    sent_state = {
        t: {"score": d["avg_score"], "signal": d["signal"]}
        for t, d in ticker_summaries.items()
    }
    set_sentiment_scores(sent_state)
    for t, d in ticker_summaries.items():
        sig_str  = "BUY" if d["signal"] == "BULLISH" else ("SELL" if d["signal"] == "BEARISH" else "HOLD")
        conf     = min(1.0, abs(d["avg_score"]) * 2.5 + 0.25)
        set_signal(t, sig_str, conf, "Sentiment")

    df_hl = pd.DataFrame(all_headlines)

    st.session_state["ns_results"] = {
        "df_hl":     df_hl,
        "summaries": ticker_summaries,
        "tickers":   tickers,
    }
    st.success(f"✓ Fetched {len(all_headlines)} headlines across {len(tickers)} tickers.")

# ── Results ───────────────────────────────────────────────────────────────────
if "ns_results" not in st.session_state:
    st.stop()

res       = st.session_state["ns_results"]
df_hl     = res["df_hl"]
summaries = res["summaries"]
tickers   = res["tickers"]

# ── Ticker summary table ──────────────────────────────────────────────────────
section("Ticker Sentiment Summary")

summary_rows = []
for t in tickers:
    d = summaries.get(t, {})
    summary_rows.append({
        "Ticker":    t,
        "Signal":    d.get("signal", "NEUTRAL"),
        "Avg Score": f"{d.get('avg_score', 0):.3f}",
        "Headlines": d.get("count", 0),
        "Bullish":   d.get("positive", 0),
        "Bearish":   d.get("negative", 0),
        "Neutral":   d.get("neutral", 0),
    })

df_sum = pd.DataFrame(summary_rows).set_index("Ticker")

def _color_signal(val):
    if val == "BULLISH": return "color:#10B981;font-weight:700"
    if val == "BEARISH": return "color:#EF4444;font-weight:700"
    return "color:#F59E0B"

def _color_score(val):
    try:
        v = float(val)
        if v > 0.05:  return "color:#10B981"
        if v < -0.05: return "color:#EF4444"
    except Exception:
        pass
    return "color:#F59E0B"

styled_sum = (
    df_sum.style
    .applymap(_color_signal, subset=["Signal"])
    .applymap(_color_score,  subset=["Avg Score"])
)
st.dataframe(styled_sum, use_container_width=True)

# ── Sentiment bar chart ───────────────────────────────────────────────────────
section("Sentiment Scores by Ticker")
t_list = [t for t in tickers if t in summaries]
s_list = [summaries[t]["avg_score"] for t in t_list]
c_list = [_GREEN if s > 0.05 else (_RED if s < -0.05 else _AMBER) for s in s_list]

fig_s = go.Figure(go.Bar(
    x=t_list, y=s_list,
    marker=dict(color=c_list, line=dict(width=0)),
    text=[f"{v:+.3f}" for v in s_list],
    textposition="outside",
    textfont=dict(family="JetBrains Mono, monospace", size=10, color="#E2E8F0"),
))
fig_s.add_hline(y=0,     line_dash="solid", line_color="#334155", line_width=1)
fig_s.add_hline(y=0.05,  line_dash="dot",   line_color=_GREEN,   line_width=1,
                annotation_text="Bullish threshold", annotation_font_color=_GREEN)
fig_s.add_hline(y=-0.05, line_dash="dot",   line_color=_RED,     line_width=1,
                annotation_text="Bearish threshold", annotation_font_color=_RED)
fig_s.update_layout(
    **plotly_config(
        height=300, margin=dict(l=0, r=0, t=20, b=40),
        yaxis=dict(range=[-0.55, 0.75], title="Avg Sentiment Score"),
        xaxis=dict(tickfont=dict(family="JetBrains Mono", size=11)),
    ),
    bargap=0.30,
)
st.plotly_chart(fig_s, use_container_width=True)

# ── Sentiment stacked bar (pos/neg/neu) ───────────────────────────────────────
section("Headline Breakdown by Category")
fig_stack = go.Figure()
for label, key, color in [
    ("Bullish", "positive", _GREEN),
    ("Neutral", "neutral",  _AMBER),
    ("Bearish", "negative", _RED),
]:
    vals = [summaries.get(t, {}).get(key, 0) for t in t_list]
    fig_stack.add_trace(go.Bar(
        name=label, x=t_list, y=vals,
        marker_color=color,
    ))
fig_stack.update_layout(
    barmode="stack",
    **plotly_config(height=300, margin=dict(l=0, r=0, t=20, b=40)),
    yaxis_title="Headline Count",
    legend=dict(font=dict(family="JetBrains Mono", size=10), orientation="h", y=1.1),
    bargap=0.25,
)
st.plotly_chart(fig_stack, use_container_width=True)

# ── Headline feed ─────────────────────────────────────────────────────────────
section("Headline Feed", "Click a column header to sort · Filter by ticker and signal below")

ticker_filter = st.multiselect(
    "Filter by ticker", options=tickers, default=tickers, key="ns_tf",
)
signal_filter = st.multiselect(
    "Filter by sentiment",
    options=["Positive","Neutral","Negative"],
    default=["Positive","Negative","Neutral"],
    key="ns_sf",
)

def _signal_cat(score: float) -> str:
    if score > 0.1:  return "Positive"
    if score < -0.1: return "Negative"
    return "Neutral"

if not df_hl.empty:
    display = df_hl[df_hl["ticker"].isin(ticker_filter)].copy()
    display["Sentiment"] = display["score"].apply(_signal_cat)
    display = display[display["Sentiment"].isin(signal_filter)]

    display_out = display[["ticker","title","Sentiment","score","pub"]].rename(columns={
        "ticker": "Ticker", "title": "Headline", "score": "Score", "pub": "Published",
    })
    display_out["Score"] = display_out["Score"].round(3)

    def _color_sent(val):
        if val == "Positive": return "color:#10B981;font-weight:600"
        if val == "Negative": return "color:#EF4444;font-weight:600"
        return "color:#F59E0B"

    styled_hl = (
        display_out.style
        .applymap(_color_sent, subset=["Sentiment"])
    )
    st.dataframe(styled_hl, use_container_width=True, height=500)

    csv_bytes = display_out.to_csv(index=False).encode()
    st.download_button(
        "⬇ Download Headlines CSV",
        data=csv_bytes,
        file_name=f"sentiment_{datetime.today().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
else:
    st.info("No headlines returned. Check ticker symbols and internet connectivity.")

# ── Methodology note ──────────────────────────────────────────────────────────
with st.expander("📖 Methodology"):
    st.markdown(
        f"""
**Data source**: Google News RSS (no API key required, updates every ~15 min).

**Scoring algorithm**:
- Each word in the headline + summary is matched against curated **{len(_POSITIVE)} positive** and **{len(_NEGATIVE)} negative** financial terms.
- Intensifiers (very, highly, sharply, etc.) multiply the word score by **1.6×**.
- Negators (not, no, never, doesn't, etc.) flip the sign.
- Raw score is clamped to [−5, +5] then normalized to [−1, +1].

**Signal thresholds**:
- Avg score > +0.05 → **BULLISH** (mapped to BUY in platform signals)
- Avg score < −0.05 → **BEARISH** (mapped to SELL in platform signals)
- Otherwise → **NEUTRAL** (HOLD)

**Limitations**: Rule-based scoring can miss nuanced context, sarcasm, and complex financial language. Use as one overlay among multiple signals, not a standalone trading trigger.
"""
    )

next_step("Open ML Alpha Lab for a data-driven overlay, or Trading Sim to paper-trade these signals.")
