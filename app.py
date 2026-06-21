import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

from auth import authenticate, save_user
from components.layout import (
    inject_global_css, plotly_config,
    sidebar_brand, render_sidebar_nav,
    _market_is_open, _fetch_ticker_strip, _fetch_spy_sidebar,
    market_ticker,
    _AMBER, _CYAN, _GREEN, _RED, _BG, _BG_CARD, _TEXT_PRI, _TEXT_SEC, _TEXT_MUT,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Quant Terminal · Command Center",
    layout="wide",
    page_icon="⚡",
)

# ── Landing page specific CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Hero section ── */
.lp-hero {
    position: relative;
    text-align: center;
    padding: 36px 32px 36px;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 24px;
    background:
        radial-gradient(ellipse at 15% 0%,   rgba(245,158,11,0.10) 0%, transparent 55%),
        radial-gradient(ellipse at 85% 100%,  rgba(6,182,212,0.07)  0%, transparent 50%),
        radial-gradient(ellipse at 50% 50%,  rgba(16,185,129,0.04)  0%, transparent 70%),
        linear-gradient(160deg, #060B14 0%, #0A1020 50%, #060B14 100%);
    border: 1px solid rgba(245,158,11,0.16);
    border-top: 1px solid rgba(245,158,11,0.40);
    box-shadow: 0 32px 80px rgba(0,0,0,0.70);
}

.lp-hero::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg,
        transparent 0%, #F59E0B 25%, #06B6D4 75%, transparent 100%);
    opacity: 0.65;
}

/* Subtle grid texture */
.lp-hero::after {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(245,158,11,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(245,158,11,0.025) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
}

.lp-badge {
    display: inline-block;
    padding: 5px 14px;
    border-radius: 999px;
    background: rgba(245,158,11,0.10);
    border: 1px solid rgba(245,158,11,0.30);
    color: #F59E0B;
    font-weight: 700;
    font-size: 0.70rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 22px;
    position: relative;
    z-index: 1;
}

.lp-title {
    font-size: 2.8rem;
    font-weight: 900;
    letter-spacing: -0.05em;
    line-height: 1.04;
    margin-bottom: 14px;
    position: relative;
    z-index: 1;
    background: linear-gradient(110deg, #F1F5F9 0%, #F59E0B 40%, #FCD34D 70%, #F59E0B 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.lp-tagline {
    font-size: 1.05rem;
    font-weight: 400;
    color: #64748B;
    margin-bottom: 12px;
    position: relative;
    z-index: 1;
    letter-spacing: 0.01em;
    font-family: 'Inter', sans-serif;
}

.lp-sub {
    font-size: 0.82rem;
    color: #334155;
    max-width: 580px;
    margin: 0 auto;
    line-height: 1.80;
    position: relative;
    z-index: 1;
    letter-spacing: 0.01em;
}

/* ── Status bar ── */
.status-bar {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 24px;
    margin-top: 28px;
    flex-wrap: wrap;
    position: relative;
    z-index: 1;
}

.status-chip {
    display: flex;
    align-items: center;
    gap: 7px;
    background: rgba(10,15,26,0.85);
    border: 1px solid rgba(245,158,11,0.18);
    border-radius: 6px;
    padding: 6px 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.70rem;
    font-weight: 700;
    color: #94A3B8;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.status-chip .val { color: #E2E8F0; margin-left: 4px; }
.status-chip .green { color: #10B981; }
.status-chip .amber { color: #F59E0B; }
.status-chip .red   { color: #EF4444; }
.status-chip .cyan  { color: #06B6D4; }

/* ── Market pulse section ── */
.pulse-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    font-weight: 700;
    color: #F59E0B;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    opacity: 0.75;
    margin: 20px 0 8px;
}

/* ── Feature cards ── */
.fc-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin: 20px 0;
}

/* Card open button — flush with bottom of card */
div[data-testid="stColumns"] div[data-testid="stButton"] button {
    background: transparent !important;
    border: 1px solid rgba(245,158,11,0.35) !important;
    border-radius: 5px !important;
    color: #F59E0B !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.10em !important;
    text-transform: uppercase !important;
    padding: 5px 14px !important;
    margin-top: -4px !important;
    transition: all 0.15s ease !important;
}
div[data-testid="stColumns"] div[data-testid="stButton"] button:hover {
    background: rgba(245,158,11,0.12) !important;
    border-color: #F59E0B !important;
    box-shadow: 0 0 12px rgba(245,158,11,0.18) !important;
}

.fc {
    background: linear-gradient(145deg, rgba(13,20,33,0.95), rgba(17,28,46,0.88));
    border: 1px solid rgba(245,158,11,0.14);
    border-top: 2px solid #F59E0B;
    border-radius: 10px;
    padding: 22px 20px 18px;
    position: relative;
    overflow: hidden;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    animation: fadeInUp 0.5s ease both;
}

.fc::after {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 100px; height: 100px;
    background: radial-gradient(circle, rgba(245,158,11,0.06), transparent 70%);
    pointer-events: none;
}

.fc:hover {
    transform: translateY(-3px);
    box-shadow: 0 16px 40px rgba(0,0,0,0.45), 0 0 0 1px rgba(245,158,11,0.22);
    border-color: rgba(245,158,11,0.38);
}

.fc:hover .fc-arrow {
    opacity: 1;
    transform: translateX(0);
}

.fc-arrow {
    position: absolute;
    bottom: 18px;
    right: 18px;
    font-size: 1rem;
    color: #F59E0B;
    opacity: 0;
    transform: translateX(-6px);
    transition: opacity 0.18s ease, transform 0.18s ease;
}

.fc-icon {
    font-size: 1.4rem;
    margin-bottom: 10px;
    display: block;
}

.fc-title {
    color: #E2E8F0;
    font-size: 0.92rem;
    font-weight: 800;
    margin-bottom: 7px;
    letter-spacing: -0.01em;
}

.fc-text {
    color: #475569;
    font-size: 0.81rem;
    line-height: 1.58;
    margin-bottom: 12px;
}

.fc-stat {
    display: inline-block;
    background: rgba(245,158,11,0.09);
    border: 1px solid rgba(245,158,11,0.20);
    color: #F59E0B;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    padding: 3px 9px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Preview panel ── */
.preview-panel {
    background: linear-gradient(135deg, rgba(13,20,33,0.95), rgba(17,28,46,0.90));
    border: 1px solid rgba(245,158,11,0.16);
    border-radius: 10px;
    padding: 22px;
    box-shadow: 0 16px 48px rgba(0,0,0,0.40);
}

.preview-title {
    color: #E2E8F0;
    font-size: 0.90rem;
    font-weight: 800;
    margin-bottom: 4px;
    font-family: 'JetBrains Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.preview-sub {
    color: #475569;
    font-size: 0.80rem;
    margin-bottom: 12px;
}

/* ── Modules panel ── */
.modules-panel {
    background: linear-gradient(135deg, rgba(13,20,33,0.95), rgba(17,28,46,0.90));
    border: 1px solid rgba(245,158,11,0.14);
    border-radius: 10px;
    padding: 22px;
    min-height: 320px;
    box-shadow: 0 16px 48px rgba(0,0,0,0.40);
}

.module-row {
    color: #94A3B8;
    font-size: 0.82rem;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'JetBrains Mono', monospace;
    transition: color 0.14s ease;
}

.module-row:hover { color: #F59E0B; }

.module-dot {
    width: 5px; height: 5px;
    border-radius: 50%;
    background: #F59E0B;
    flex-shrink: 0;
    opacity: 0.70;
}

.online-chip {
    margin-top: 20px;
    background: rgba(16,185,129,0.08);
    border: 1px solid rgba(16,185,129,0.22);
    border-radius: 6px;
    padding: 9px 13px;
    color: #10B981;
    font-weight: 700;
    font-size: 0.70rem;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Quant rain background ── */
@keyframes qrain {
    0%   { transform: translateY(0); }
    100% { transform: translateY(-50%); }
}
.quant-rain {
    position: fixed;
    inset: 0;
    z-index: -1;
    pointer-events: none;
    overflow: hidden;
}
.qr-col {
    position: absolute;
    top: 0;
    font-family: 'JetBrains Mono', Courier New, monospace;
    line-height: 1.88;
    white-space: pre;
    animation: qrain linear infinite;
    user-select: none;
    will-change: transform;
}
</style>
""", unsafe_allow_html=True)


inject_global_css()
sidebar_brand()
render_sidebar_nav()

# ── Bloomberg terminal quant rain background ──────────────────────────────────
_C_AMB = "#F59E0B"
_C_GRN = "#10B981"
_C_CYN = "#06B6D4"

def _qcol(data, left, dur, delay, color, opacity, size="0.42rem"):
    d2 = data + data  # double for seamless loop
    return (
        f'<div class="qr-col" style="left:{left};animation-duration:{dur};'
        f'animation-delay:{delay};color:{color};opacity:{opacity};font-size:{size};">'
        f'{d2}</div>'
    )

_equities = """AAPL   182.50  +1.24%   78.3M
MSFT   378.92  -0.38%  142.1M
GOOGL  155.73  +0.82%   33.7M
AMZN   178.45  +0.15%   67.8M
NVDA   875.50  +2.41%   95.2M
META   485.23  -0.92%   28.4M
TSLA   171.68  -1.47%  112.3M
BRK-B  361.22  +0.44%   15.6M
JPM    193.87  +0.73%   42.1M
V      275.34  +0.28%   18.9M
MA     441.67  +0.55%   22.1M
HD     355.89  -0.19%   11.4M
ABBV   163.24  +0.33%   13.7M
PG     155.48  -0.12%    9.8M
MRK    126.73  +0.61%   16.2M
COST   793.45  +1.12%    6.9M
NFLX   612.34  +2.31%   18.4M
AMD    152.67  -0.74%   77.6M
ADBE   524.18  +0.93%   12.3M
CRM    288.41  -0.41%   14.8M
"""

_futures = """ES1!   5237.25  -0.12%
NQ1!  18432.50  +0.35%
YM1!  38921.00  -0.08%
RTY1!  2043.60  +0.72%
CL1!     81.43  -0.84%
GC1!   2385.20  +0.22%
SI1!     28.14  -0.43%
ZN1!    108.14  +0.11%
ZB1!    117.22  -0.18%
HG1!      4.52  +0.67%
NG1!      2.31  -1.23%
ZC1!    452.25  -0.55%
ZS1!   1245.50  +0.34%
ZW1!    575.25  -0.22%
VIX      14.82  +3.21%
MOVE    107.34  -1.42%
DX1!    104.83  +0.18%
6E1!      1.085 -0.23%
6J1!    152.38  +0.45%
6B1!      1.264 -0.17%
"""

_risk = """PORTFOLIO RISK
Sharpe     1.842
Sortino    2.341
Max DD    -8.43%
VaR 95%    1.82%
CVaR 95%   2.34%
Beta       0.847
Corr SPY   0.923
IR         0.412
Turnover  18.3%
Ann Vol   14.2%
Ann Ret   22.7%
Info Ratio 1.12
Calmar     2.67
Omega      1.93
Treynor   26.8%
Jensen A   8.3%
Skewness  -0.34
Kurtosis   1.87
Hit Rate  58.2%
W/L Ratio  1.64
"""

_orderflow = """09:30:01 AAPL BUY  5000 182.50
09:30:14 MSFT SELL 2000 378.92
09:30:28 NVDA BUY  1000 875.50
09:31:03 META BUY  3000 485.23
09:31:15 GOOGL SELL 1500 155.73
09:31:42 TSLA SELL 4000 171.68
09:32:11 AMZN BUY  2500 178.45
09:32:34 JPM  BUY  6000 193.87
09:33:02 V    SELL 3500 275.34
09:33:19 MA   BUY  2000 441.67
09:33:45 COST BUY   500 793.45
09:34:12 HD   SELL 1200 355.89
09:34:38 NFLX BUY   800 612.34
09:35:01 AMD  SELL 4500 152.67
09:35:22 ABBV BUY  2800 163.24
09:35:47 PG   BUY  3200 155.48
09:36:14 MRK  SELL  900 126.73
09:36:38 BRK  BUY  1500 361.22
09:37:05 ADBE BUY   700 524.18
09:37:28 CRM  SELL 2100 288.41
"""

_factors = """FACTOR RESEARCH

Momentum  Rank
NVDA 0.947  #1
MSFT 0.891  #2
AAPL 0.834  #3
META 0.823  #4
AMZN 0.801  #5

Value     Rank
BRK  0.912  #1
JPM  0.887  #2
V    0.856  #3
MA   0.834  #4

Quality   Rank
MSFT 0.934  #1
AAPL 0.923  #2
GOOGL 0.912 #3

Low-Vol   Rank
PG   0.941  #1
ABBV 0.923  #2
MRK  0.908  #3
"""

_mlsignals = """ML ALPHA SIGNALS

AAPL  BUY  0.847
MSFT  BUY  0.823
GOOGL HOLD 0.612
AMZN  BUY  0.791
NVDA  BUY  0.934
META  SELL 0.712
TSLA  SELL 0.683
BRK-B HOLD 0.541
JPM   BUY  0.762
V     BUY  0.801
MA    BUY  0.778
COST  HOLD 0.590
HD    HOLD 0.553
NFLX  BUY  0.831
AMD   SELL 0.647
ABBV  HOLD 0.518
PG    BUY  0.693
MRK   BUY  0.721
ADBE  BUY  0.803
CRM   HOLD 0.567
"""

_depth = """MARKET DEPTH

AAPL 182.50
BID  182.48  1,200
     182.47  3,400
     182.46  5,600
ASK  182.52    900
     182.53  2,100
     182.54  4,300
SPREAD  $0.04

NVDA 875.50
BID  875.45  2,300
     875.40  4,100
     875.35  6,700
ASK  875.55  1,500
     875.60  2,900
     875.65  5,100
SPREAD  $0.10

MSFT 378.92
BID  378.90  1,800
     378.88  3,200
ASK  378.94  1,200
     378.96  2,400
SPREAD  $0.04
"""

_sentiment = """NEWS SENTIMENT

AAPL  +0.342  BULL
MSFT  +0.281  BULL
GOOGL +0.112  BULL
META  -0.234  BEAR
TSLA  -0.445  BEAR
NVDA  +0.523  BULL
AMZN  +0.198  BULL
JPM   +0.087  BULL
BRK-B +0.156  BULL
AMD   -0.112  BEAR
V     +0.231  BULL
MA    +0.195  BULL
COST  +0.267  BULL
HD    -0.043  NEUT
NFLX  +0.389  BULL
ABBV  +0.123  BULL
PG    +0.089  BULL
MRK   +0.201  BULL
ADBE  +0.314  BULL
CRM   -0.078  NEUT
"""

_vol = """IMPL VOL SURFACE
NVDA  07/19 Exp
      C      P
 80% 0.612  0.618
 90% 0.523  0.529
100% 0.451  0.456
110% 0.389  0.395
120% 0.334  0.341
AAPL  07/19 Exp
      C      P
 80% 0.281  0.287
 90% 0.247  0.252
100% 0.218  0.223
110% 0.192  0.198
120% 0.169  0.175
SKEW  -12  -10  -8
KURT   3.2  2.9  2.6
VEGA WEIGHTED IV
30D  14.8%  60D 15.7%
"""

_crypto = """CRYPTO PRICES

BTC  67,234  -0.31%
ETH   3,512  +1.23%
BNB     412  -0.82%
SOL     167  +2.14%
ADA    0.48  -1.42%
DOT    8.92  +0.63%
AVAX   39.4  +1.83%
LINK   18.7  -0.51%
MATIC  0.91  +0.31%
ATOM    9.8  -0.91%

DOMINANCE
BTC   52.3%
ETH   17.8%
ALTs  29.9%

FEAR/GREED  63
FUNDING  0.0102%
OPEN INT  $28.4B
"""

_bg_html = '<div class="quant-rain">' + "".join([
    _qcol(_equities,   " 1%", "36s", "  0s", _C_AMB, "0.055"),
    _qcol(_futures,    "12%", "30s", " -8s", _C_GRN, "0.050"),
    _qcol(_risk,       "22%", "42s", "-15s", _C_CYN, "0.045"),
    _qcol(_orderflow,  "33%", "28s", " -5s", _C_AMB, "0.040", "0.38rem"),
    _qcol(_factors,    "44%", "38s", "-22s", _C_GRN, "0.045"),
    _qcol(_mlsignals,  "55%", "32s", "-11s", _C_CYN, "0.042"),
    _qcol(_depth,      "65%", "44s", "-18s", _C_AMB, "0.038"),
    _qcol(_sentiment,  "75%", "34s", " -3s", _C_GRN, "0.048"),
    _qcol(_vol,        "84%", "40s", "-26s", _C_CYN, "0.040", "0.38rem"),
    _qcol(_crypto,     "93%", "29s", "-14s", _C_AMB, "0.043"),
]) + "</div>"

st.markdown(_bg_html, unsafe_allow_html=True)

# ── Session state bootstrap ───────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username  = None

# ── Auth (inline in main content — sidebar is hidden) ────────────────────────
_auth_placeholder = st.empty()

def _render_auth():
    with _auth_placeholder.container():
        if not st.session_state.get("logged_in", False):
            with st.expander("🔐 Sign In / Register", expanded=False):
                tab_login, tab_reg = st.tabs(["Login", "Register"])
                with tab_login:
                    username = st.text_input("Username", key="login_username")
                    password = st.text_input("Password", type="password", key="login_password")
                    if st.button("Login", use_container_width=True):
                        if authenticate(username, password):
                            st.session_state.logged_in = True
                            st.session_state.username  = username
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
                with tab_reg:
                    new_user = st.text_input("New Username", key="register_username")
                    new_pass = st.text_input("New Password", type="password", key="register_password")
                    if st.button("Register", use_container_width=True):
                        if save_user(new_user, new_pass):
                            st.success("Account created — please log in.")
                        else:
                            st.error("Username already exists")
        else:
            uname = st.session_state.get("username", "")
            c1, c2 = st.columns([4, 1])
            c1.markdown(
                f"<span style='color:#10B981;font-weight:700;font-size:0.78rem;"
                f"font-family:JetBrains Mono,monospace;'>● SIGNED IN · {uname.upper()}</span>",
                unsafe_allow_html=True,
            )
            if c2.button("Sign Out"):
                st.session_state.clear()
                st.rerun()

_render_auth()


# ── Status bar data ───────────────────────────────────────────────────────────
mkt_open = _market_is_open()
try:
    et  = pytz.timezone("America/New_York")
    now_str = datetime.now(et).strftime("%H:%M:%S ET")
except Exception:
    now_str = datetime.now().strftime("%H:%M:%S")

spy_price = _fetch_spy_sidebar()
spy_str   = f"${spy_price:,.2f}" if spy_price else "N/A"
mkt_color = "green" if mkt_open else "red"
mkt_txt   = "OPEN" if mkt_open else "CLOSED"


market_ticker()

# ── Hero section ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="lp-hero">
    <div class="lp-badge">⚡ Institutional Quantitative Research Platform</div>
    <div class="lp-title">Quant Terminal</div>
    <div class="lp-tagline">Professional-grade quantitative research &amp; risk analytics.</div>
    <div class="lp-sub">
        Portfolio optimization · Monte Carlo simulation · Real-time risk monitoring ·
        Market anomaly detection · Algorithmic backtesting · Options Greeks
    </div>
    <div class="status-bar">
        <div class="status-chip">
            <span class="{mkt_color}">●</span> NYSE
            <span class="val {mkt_color}">{mkt_txt}</span>
        </div>
        <div class="status-chip">
            🕐 <span class="val">{now_str}</span>
        </div>
        <div class="status-chip">
            SPY <span class="val amber">{spy_str}</span>
        </div>
        <div class="status-chip">
            <span class="cyan">●</span> Systems
            <span class="val cyan">ONLINE</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── KPI strip ─────────────────────────────────────────────────────────────────
_eq   = st.session_state.get("equity_curve")
_rets = st.session_state.get("strategy_returns")
_cap  = st.session_state.get("initial_capital")

def _fmt_kpi(val, fmt):
    try:
        return fmt.format(val)
    except Exception:
        return "—"

if _eq is not None and _rets is not None and len(_rets) > 5:
    import numpy as np, pandas as pd
    _eq_s   = pd.Series(_eq) if not hasattr(_eq, 'iloc') else _eq
    _ret_s  = pd.Series(_rets) if not hasattr(_rets, 'iloc') else _rets
    _pval   = float(_eq_s.iloc[-1])
    _dpnl   = float(_ret_s.iloc[-1] * _eq_s.iloc[-2]) if len(_ret_s) > 1 else 0.0
    _sharpe = float((_ret_s.mean() / (_ret_s.std() + 1e-9)) * np.sqrt(252))
    _peak   = _eq_s.cummax()
    _maxdd  = float((_eq_s / _peak - 1).min())
    # simple SPY-based regime
    try:
        import yfinance as yf
        _spy = yf.download("SPY", period="60d", interval="1d", auto_adjust=True, progress=False)["Close"].squeeze().dropna()
        _regime = "BULL" if float(_spy.iloc[-1]) > float(_spy.rolling(50).mean().iloc[-1]) else "BEAR"
    except Exception:
        _regime = "—"
    _kpi_data = [
        ("PORTFOLIO VALUE", f"${_pval:,.0f}", None),
        ("DAILY PnL",       f"${_dpnl:+,.0f}", "green" if _dpnl >= 0 else "red"),
        ("SHARPE RATIO",    f"{_sharpe:.2f}", "green" if _sharpe > 1 else ("amber" if _sharpe > 0 else "red")),
        ("MAX DRAWDOWN",    f"{_maxdd*100:.1f}%", "red" if _maxdd < -0.1 else "amber"),
        ("MARKET REGIME",   _regime, "green" if _regime == "BULL" else "red"),
    ]
    _has_data = True
else:
    _kpi_data = [
        ("PORTFOLIO VALUE", "—", None),
        ("DAILY PnL",       "—", None),
        ("SHARPE RATIO",    "—", None),
        ("MAX DRAWDOWN",    "—", None),
        ("MARKET REGIME",   "—", None),
    ]
    _has_data = False

_kpi_cols = st.columns(5)
for _col, (label, val, color) in zip(_kpi_cols, _kpi_data):
    _val_color = {"green": "#10B981", "red": "#EF4444", "amber": "#F59E0B"}.get(color, "#E2E8F0")
    _col.markdown(f"""
        <div style="background:rgba(13,20,33,0.80);border:1px solid rgba(245,158,11,0.12);
            border-top:2px solid rgba(245,158,11,0.35);border-radius:8px;padding:12px 14px 10px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.52rem;font-weight:800;
                color:#475569;text-transform:uppercase;letter-spacing:0.16em;margin-bottom:6px;">{label}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;
                color:{_val_color};letter-spacing:-0.01em;">{val}</div>
        </div>""", unsafe_allow_html=True)

if not _has_data:
    st.markdown('<div style="text-align:center;font-size:0.72rem;color:#334155;font-family:Inter,sans-serif;margin-top:6px;">Run a backtest or simulation to populate live metrics</div>', unsafe_allow_html=True)
    st.page_link("pages/1_backtest.py", label="→ Run Backtest")


# ── CTA nav row ───────────────────────────────────────────────────────────────
nav1, nav2, nav3, nav4 = st.columns(4)
with nav1:
    st.page_link("pages/0_dashboard.py",    label="Open Dashboard",  icon="📊")
with nav2:
    st.page_link("pages/2_Market_Prices.py", label="Market Prices",  icon="📈")
with nav3:
    st.page_link("pages/10_RiskEngine.py",  label="Risk Engine",     icon="🛡️")
with nav4:
    st.page_link("pages/11_MonteCarlo.py",  label="Monte Carlo",     icon="🎲")


# ── Market Pulse ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _fetch_pulse():
    try:
        from market.prices import fetch_latest_prices
        return fetch_latest_prices(
            ["SPY", "QQQ", "NVDA", "AAPL", "TSLA", "BTC-USD"],
            period="5d", interval="1d",
        )
    except Exception:
        return pd.DataFrame()


_pulse_df = _fetch_pulse()
if not _pulse_df.empty:
    st.markdown(
        f"<div class='pulse-label'>▶ Market Pulse · ~15 min delayed · {datetime.now().strftime('%H:%M')}</div>",
        unsafe_allow_html=True,
    )
    _pc = st.columns(6)
    for _pcol, (_tkr, _row) in zip(_pc, _pulse_df.iterrows()):
        _price_str = (
            f"${_row['price']:,.0f}" if _row["price"] >= 1000
            else f"${_row['price']:,.2f}"
        )
        _pcol.metric(_tkr, _price_str, f"{_row['pct_change']:+.2f}%")
    st.markdown("<br>", unsafe_allow_html=True)


# ── Feature cards ─────────────────────────────────────────────────────────────
_cards = [
    ("🛡️", "Risk Engine",
     "Real-time drawdown, volatility, Sharpe ratio, worst-period loss, and kill-switch monitoring.",
     "8 LIVE METRICS", "pages/10_RiskEngine.py"),
    ("🎲", "Monte Carlo",
     "Forward portfolio simulations, scenario stress-testing, and probability-based return forecasting.",
     "10 K+ SIMULATIONS", "pages/11_MonteCarlo.py"),
    ("📊", "Optimizer",
     "Max Sharpe, min volatility, equal-weight, and risk-parity portfolio construction.",
     "4 MODES", "pages/16_Portfolio_Optimizer.py"),
    ("⚡", "Execution Sim",
     "TWAP · VWAP · Adaptive execution engine with market impact and implementation shortfall.",
     "INSTITUTIONAL GRADE", "pages/8_Execution.py"),
]

# Render cards as columns so st.switch_page works reliably
_fc_cols = st.columns(4)
for _col, (icon, title, text, stat, page_path) in zip(_fc_cols, _cards):
    with _col:
        st.markdown(f"""
        <div class="fc">
            <span class="fc-icon">{icon}</span>
            <div class="fc-title">{title}</div>
            <div class="fc-text">{text}</div>
            <span class="fc-stat">{stat}</span>
            <span class="fc-arrow">→</span>
        </div>""", unsafe_allow_html=True)
        _btn_labels = {
            "Risk Engine": "Enter Risk Engine",
            "Monte Carlo": "Open Research",
            "Optimizer": "Launch Optimizer",
            "Execution Sim": "Open Terminal",
        }
        _btn_label = _btn_labels.get(title, "Open →")
        if st.button(_btn_label, key=f"fc_{title}", use_container_width=True):
            st.switch_page(page_path)


# ── New institutional modules row ─────────────────────────────────────────────
st.markdown(
    f"<div style='font-family:JetBrains Mono,monospace;font-size:0.62rem;font-weight:800;"
    f"color:#F59E0B;text-transform:uppercase;letter-spacing:0.18em;opacity:0.75;"
    f"margin:20px 0 12px;'>◈ New · Institutional Research Modules</div>",
    unsafe_allow_html=True,
)
_new_cards = [
    ("🔬", "Factor Research",
     "Multi-factor equity ranking: Momentum · Value · Quality · Profitability · Low-Vol with cross-sectional scoring.",
     "5 FACTORS", "pages/22_Factor_Research.py"),
    ("🤖", "ML Alpha Lab",
     "Random Forest, Gradient Boosting & Logistic Regression signal generation with walk-forward validation.",
     "3 MODELS", "pages/23_ML_Alpha_Lab.py"),
    ("📰", "News Sentiment",
     "Rule-based sentiment scoring from Google News RSS — no paid APIs. Ticker-level bullish/bearish signals.",
     "REAL-TIME RSS", "pages/24_News_Sentiment.py"),
    ("💹", "Paper Trading",
     "Sim broker + Alpaca paper-trading integration with risk checks, kill switch, and broker status card.",
     "ALPACA READY", "pages/5_Trading_Sim.py"),
]
_new_cols = st.columns(4)
for _col, (icon, title, text, stat, page_path) in zip(_new_cols, _new_cards):
    with _col:
        st.markdown(f"""
        <div class="fc" style="border-top-color:{_CYAN};">
            <span class="fc-icon">{icon}</span>
            <div class="fc-title">{title}</div>
            <div class="fc-text">{text}</div>
            <span class="fc-stat" style="border-color:rgba(6,182,212,0.30);
                background:rgba(6,182,212,0.09);color:{_CYAN};">{stat}</span>
            <span class="fc-arrow">→</span>
        </div>""", unsafe_allow_html=True)
        if st.button(f"Open {title}", key=f"nc_{title}", use_container_width=True):
            st.switch_page(page_path)

# ── Preview + modules panel ───────────────────────────────────────────────────
v1, v2 = st.columns([1.55, 1])

with v1:
    st.markdown("""
    <div class="preview-panel">
        <div class="preview-title">📈 Strategy Performance Preview</div>
        <div class="preview-sub">Simulated quant equity curve vs benchmark — risk-aware execution.</div>
    </div>
    """, unsafe_allow_html=True)

    equity_preview = st.session_state.get("equity_curve", None)
    if equity_preview is not None and len(equity_preview) > 0:
        _pv = list(pd.Series(equity_preview).reset_index(drop=True))
        _n  = len(_pv)
        _bench = [100 * (1 + 0.0004) ** i for i in range(_n)]
    else:
        _pv    = [100,103,101,108,115,112,121,132,129,141,153,160,
                  158,168,175,172,183,191,188,201,210,207,220,234]
        _bench = [100 * (1 + 0.0003) ** i for i in range(len(_pv))]

    preview_fig = go.Figure()
    preview_fig.add_trace(go.Scatter(
        y=_pv, mode="lines", name="Strategy",
        line=dict(color=_AMBER, width=2.2),
        fill="tozeroy", fillcolor="rgba(245,158,11,0.06)",
    ))
    preview_fig.add_trace(go.Scatter(
        y=_bench, mode="lines", name="Benchmark",
        line=dict(color=_CYAN, width=1.5, dash="dot"),
    ))
    preview_fig.add_annotation(
        x=len(_pv)-1, y=_pv[-1],
        text=f"+{(_pv[-1]/_pv[0]-1)*100:.1f}%",
        showarrow=False,
        font=dict(color=_AMBER, size=11, family="JetBrains Mono, monospace"),
        bgcolor="rgba(10,15,26,0.85)", bordercolor=_AMBER, borderwidth=1,
        xanchor="right",
    )
    preview_fig.update_layout(
        **plotly_config(
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            showlegend=False, height=220,
        ),
    )
    st.plotly_chart(preview_fig, use_container_width=True, config={"displayModeBar": False})

with v2:
    st.markdown("""
    <div class="modules-panel">
        <div style="color:#F59E0B;font-size:0.70rem;font-weight:800;
                    font-family:'JetBrains Mono',monospace;letter-spacing:0.12em;
                    text-transform:uppercase;margin-bottom:14px;opacity:0.85;">
            ⬡ Quant Modules
        </div>
        <div class="module-row"><span class="module-dot"></span>Monte Carlo Forecasting</div>
        <div class="module-row"><span class="module-dot"></span>Portfolio Optimization</div>
        <div class="module-row"><span class="module-dot"></span>Market Regime Detection</div>
        <div class="module-row"><span class="module-dot"></span>Risk Monitoring Engine</div>
        <div class="module-row"><span class="module-dot"></span>Pairs Trading &amp; Cointegration</div>
        <div class="module-row"><span class="module-dot"></span>Order Book Microstructure</div>
        <div class="module-row"><span class="module-dot"></span>TWAP / VWAP Execution</div>
        <div class="module-row"><span class="module-dot"></span>Options Pricing + Greeks</div>
        <div class="module-row"><span class="module-dot"></span>VaR / CVaR Analytics</div>
        <div class="module-row" style="color:#06B6D4;"><span style="background:#06B6D4;" class="module-dot"></span>🔬 Factor Research Engine</div>
        <div class="module-row" style="color:#06B6D4;"><span style="background:#06B6D4;" class="module-dot"></span>🤖 ML Alpha Lab</div>
        <div class="module-row" style="color:#06B6D4;"><span style="background:#06B6D4;" class="module-dot"></span>📰 News Sentiment Engine</div>
        <div class="module-row" style="color:#06B6D4;"><span style="background:#06B6D4;" class="module-dot"></span>💹 Alpaca Paper Trading</div>
        <div class="online-chip">● Research Terminal Online · 13 Modules Active</div>
    </div>
    """, unsafe_allow_html=True)


# ── Gate: stop here for unauthenticated visitors ──────────────────────────────
if not st.session_state.get("logged_in", False):
    st.stop()

# ── Logged-in welcome ─────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
username = st.session_state.get("username", "Trader")
st.markdown(
    f"<div style='font-family:JetBrains Mono,monospace;font-size:1.05rem;"
    f"font-weight:800;color:#F59E0B;letter-spacing:0.04em;margin-bottom:14px;'>"
    f"▶ WELCOME BACK, {username.upper()} — SELECT MODULE</div>",
    unsafe_allow_html=True,
)

wc1, wc2, wc3, wc4 = st.columns(4)
with wc1:
    st.page_link("pages/1_backtest.py",          label="Run Backtest",     icon="🧪")
with wc2:
    st.page_link("pages/0_dashboard.py",         label="Dashboard",        icon="📊")
with wc3:
    st.page_link("pages/10_RiskEngine.py",       label="Risk Engine",      icon="🛡️")
with wc4:
    st.page_link("pages/11_MonteCarlo.py",       label="Monte Carlo",      icon="🎲")

wc5, wc6, wc7, wc8 = st.columns(4)
with wc5:
    st.page_link("pages/22_Factor_Research.py",  label="Factor Research",  icon="🔬")
with wc6:
    st.page_link("pages/23_ML_Alpha_Lab.py",     label="ML Alpha Lab",     icon="🤖")
with wc7:
    st.page_link("pages/24_News_Sentiment.py",   label="News Sentiment",   icon="📰")
with wc8:
    st.page_link("pages/5_Trading_Sim.py",       label="Paper Trading",    icon="💹")
