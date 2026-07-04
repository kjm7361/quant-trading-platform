import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf

from execution.sim_broker import get_cash, get_positions, list_trades
from components.layout import (
    setup_page, section, next_step, plotly_config, nav_hub,
    workflow_breadcrumb, _AMBER, _CYAN, _GREEN, _RED,
)


# ── Cached market data ────────────────────────────────────────────────────────

_PULSE_SYMS = ["SPY", "QQQ", "NVDA", "AAPL", "BTC-USD", "TSLA"]

@st.cache_data(ttl=300)
def _market_overview():
    try:
        from market.prices import fetch_latest_prices
        result = fetch_latest_prices(_PULSE_SYMS, period="5d", interval="1d")
        if not result.empty:
            return result
    except Exception:
        pass
    # Fallback: direct yfinance download using pattern already used in _spy_history()
    try:
        raw = yf.download(_PULSE_SYMS, period="5d", interval="1d",
                          auto_adjust=True, progress=False)
        if raw.empty:
            return pd.DataFrame()
        close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
        rows = {}
        for sym in _PULSE_SYMS:
            if sym in close.columns:
                s = close[sym].dropna()
                if len(s) >= 2:
                    rows[sym] = {
                        "price": float(s.iloc[-1]),
                        "pct_change": float((s.iloc[-1] / s.iloc[-2] - 1) * 100),
                    }
        return pd.DataFrame(rows).T if rows else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def _spy_history():
    try:
        return yf.download("SPY", period="60d", interval="1d",
                           auto_adjust=True, progress=False)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def _fetch_news(query="stock market investing"):
    try:
        from news.rss import google_news_rss
        return google_news_rss(query)[:6]
    except Exception:
        return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_series(x):
    if x is None:
        return pd.Series(dtype=float)
    return pd.Series(x).dropna()


def compute_drawdown(equity):
    equity = safe_series(equity)
    if len(equity) == 0:
        return pd.Series(dtype=float)
    return equity / equity.cummax() - 1


def format_pct(x):
    return f"{x * 100:.2f}%"


def format_money(x):
    return f"${x:,.2f}"


def get_portfolio_snapshot():
    cash = float(get_cash())
    positions = get_positions()
    total_market_value = 0.0
    rows = []
    for p in positions:
        symbol = str(p["symbol"]).upper().strip()
        qty = float(p["qty"])
        avg_price = float(p["avg_price"])
        market_value = qty * avg_price
        total_market_value += market_value
        rows.append({"Ticker": symbol, "Qty": qty, "Avg Price": avg_price, "Market Value": market_value})
    positions_df = pd.DataFrame(rows)
    portfolio_equity = cash + total_market_value
    if not positions_df.empty and portfolio_equity > 0:
        positions_df["Weight"] = positions_df["Market Value"] / portfolio_equity
        positions_df["Weight %"] = positions_df["Weight"] * 100
        positions_df = positions_df.sort_values("Market Value", ascending=False).reset_index(drop=True)
    return cash, total_market_value, portfolio_equity, positions_df


def build_alerts(returns, equity, kill_switch, kill_switch_reasons):
    alerts = []
    returns = safe_series(returns)
    equity = safe_series(equity)
    drawdown = compute_drawdown(equity)
    if len(equity) > 0:
        latest_drawdown = float(drawdown.iloc[-1]) if len(drawdown) > 0 else 0.0
        max_drawdown = float(drawdown.min()) if len(drawdown) > 0 else 0.0
        total_return = float((equity.iloc[-1] / equity.iloc[0]) - 1) if len(equity) > 1 else 0.0
    else:
        latest_drawdown = max_drawdown = total_return = 0.0
    if len(returns) > 0:
        rolling_vol = float(returns.tail(min(20, len(returns))).std())
        latest_return = float(returns.iloc[-1])
    else:
        rolling_vol = latest_return = 0.0
    if latest_drawdown < -0.10:
        alerts.append(("Critical", f"Current drawdown is elevated at {format_pct(latest_drawdown)}"))
    if max_drawdown < -0.15:
        alerts.append(("Warning", f"Historical max drawdown reached {format_pct(max_drawdown)}"))
    if rolling_vol > 0.05:
        alerts.append(("Warning", f"Rolling volatility is high at {rolling_vol:.4f}"))
    if latest_return < -0.03:
        alerts.append(("Critical", f"Latest period return dropped to {format_pct(latest_return)}"))
    if total_return > 0.10:
        alerts.append(("Positive", f"Portfolio above 10% gain threshold at {format_pct(total_return)}"))
    if kill_switch:
        reason_text = "; ".join(kill_switch_reasons) if kill_switch_reasons else "Risk limits exceeded"
        alerts.append(("Critical", f"Kill switch active: {reason_text}"))
    return alerts


def get_status(kill_switch, alerts):
    if kill_switch:
        return "Critical"
    if any(level == "Critical" for level, _ in alerts):
        return "Critical"
    if any(level == "Warning" for level, _ in alerts):
        return "Warning"
    if any(level == "Positive" for level, _ in alerts):
        return "Positive"
    return "Normal"


def detect_spy_regime(spy_df):
    """Simple 20/50 SMA crossover regime for SPY."""
    try:
        close = spy_df["Close"].squeeze().dropna()
        if len(close) < 50:
            return "Insufficient Data", "#94A3B8"
        sma20 = close.rolling(20).mean().iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1]
        price = close.iloc[-1]
        vol = close.pct_change().dropna().tail(20).std() * np.sqrt(252)
        if price > sma20 > sma50 and vol < 0.20:
            return "Bull", _GREEN
        elif price > sma20 > sma50 and vol >= 0.20:
            return "High-Vol Bull", _AMBER
        elif price < sma20 < sma50 and vol >= 0.22:
            return "Stress", _RED
        elif price < sma20 < sma50:
            return "Bear", _RED
        else:
            return "Sideways", _CYAN
    except Exception:
        return "Unknown", "#94A3B8"


def compute_risk_score(max_dd, rolling_vol, kill_switch):
    """0 = safe, 100 = maximum risk."""
    dd_score = min(abs(max_dd) * 300, 50)
    vol_score = min(rolling_vol * 500, 40)
    ks_score = 10 if kill_switch else 0
    return min(int(dd_score + vol_score + ks_score), 100)


# ── Load state ────────────────────────────────────────────────────────────────

setup_page(
    "Command Center",
    "Real-time portfolio intelligence, risk monitoring, and market intelligence.",
    "⚡",
)

strategy_returns = st.session_state.get("strategy_returns", None)
equity_curve = st.session_state.get("equity_curve", None)
kill_switch = st.session_state.get("kill_switch", False)
kill_switch_reasons = st.session_state.get("kill_switch_reasons", [])
bot_signal = st.session_state.get("bot_signal", "N/A")
bot_reason = st.session_state.get("bot_reason", "No bot decision stored yet.")

returns = safe_series(strategy_returns)
equity = safe_series(equity_curve)
drawdown = compute_drawdown(equity)
cash, market_value, portfolio_equity, positions_df = get_portfolio_snapshot()
trades = list_trades(limit=8)
alerts = build_alerts(returns, equity, kill_switch, kill_switch_reasons)
system_status = get_status(kill_switch, alerts)

rolling_vol = float(returns.tail(min(20, len(returns))).std()) if len(returns) > 0 else 0.0
sharpe = float((returns.mean() / (returns.std() + 1e-9)) * np.sqrt(252)) if len(returns) > 0 else 0.0
max_drawdown = float(drawdown.min()) if len(drawdown) > 0 else 0.0
total_return = float((equity.iloc[-1] / equity.iloc[0]) - 1) if len(equity) > 1 else 0.0
daily_pnl = float(returns.iloc[-1] * equity.iloc[-2]) if len(returns) > 1 and len(equity) > 1 else 0.0

spy_df = _spy_history()
regime_label, regime_color = detect_spy_regime(spy_df)
risk_score = compute_risk_score(max_drawdown, rolling_vol, kill_switch)

# ── Regime badge ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _get_regime():
    try:
        import yfinance as yf, numpy as np
        _spy = yf.download("SPY", period="200d", interval="1d", auto_adjust=True, progress=False)["Close"].squeeze().dropna()
        _price = float(_spy.iloc[-1])
        _sma50 = float(_spy.rolling(50).mean().iloc[-1])
        _sma200 = float(_spy.rolling(200).mean().iloc[-1])
        _vol = float(_spy.pct_change().dropna().tail(20).std() * (252**0.5))
        if _price > _sma50 > _sma200 and _vol < 0.18:
            return "BULL MARKET", "#10B981", "Risk-On"
        elif _price > _sma50 > _sma200 and _vol >= 0.18:
            return "HIGH-VOL BULL", "#F59E0B", "Elevated Risk"
        elif _price < _sma50 < _sma200 and _vol > 0.25:
            return "RISK-OFF", "#EF4444", "Defensive"
        elif _price < _sma50:
            return "BEAR MARKET", "#EF4444", "Risk-Off"
        else:
            return "SIDEWAYS", "#06B6D4", "Neutral"
    except Exception:
        return "UNKNOWN", "#475569", "—"

_regime_label, _regime_color, _regime_posture = _get_regime()
st.markdown(f"""
    <div style="display:inline-flex;align-items:center;gap:10px;
        background:rgba(13,20,33,0.90);border:1px solid {_regime_color}33;
        border-left:3px solid {_regime_color};border-radius:6px;
        padding:8px 16px;margin-bottom:12px;">
        <span style="width:8px;height:8px;border-radius:50%;background:{_regime_color};
            box-shadow:0 0 8px {_regime_color};display:inline-block;flex-shrink:0;"></span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;font-weight:800;
            color:{_regime_color};letter-spacing:0.12em;">REGIME: {_regime_label}</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.66rem;color:#475569;">
            {_regime_posture} · SPY 50/200 MA + Vol</span>
    </div>""", unsafe_allow_html=True)

# ── Workflow breadcrumb ───────────────────────────────────────────────────────

workflow_breadcrumb("")

# ── Status banner ─────────────────────────────────────────────────────────────

if system_status == "Critical":
    st.error(f"System Status: CRITICAL — {len(alerts)} active alert(s)")
elif system_status == "Warning":
    st.warning(f"System Status: WARNING — {len(alerts)} alert(s) require attention")
elif system_status == "Positive":
    st.success("System Status: POSITIVE — Portfolio performing well")
else:
    st.info("System Status: NORMAL — All risk parameters within bounds")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ROW 1 — 5 KPI TILES
# ═══════════════════════════════════════════════════════════════════════════════

k1, k2, k3, k4, k5 = st.columns(5)

_has_equity_history = len(equity) > 1
_has_returns = len(returns) > 5
_has_positions = market_value > 0

with k1:
    if _has_equity_history or _has_positions:
        _eq_delta = f"+{format_money(portfolio_equity - 100_000)}" if portfolio_equity >= 100_000 else format_money(portfolio_equity - 100_000)
        st.metric("Portfolio Equity", format_money(portfolio_equity), _eq_delta if _has_equity_history else None)
    else:
        st.metric("Portfolio Equity", "No portfolio", "Run Trading Sim")

with k2:
    if _has_returns:
        _pnl_str = f"+{format_money(daily_pnl)}" if daily_pnl >= 0 else format_money(daily_pnl)
        st.metric("Daily PnL (est.)", format_money(daily_pnl), _pnl_str)
    else:
        st.metric("Daily PnL (est.)", "Awaiting data", "Run backtest")

with k3:
    st.metric("Market Regime (SPY)", regime_label)

with k4:
    _risk_delta = "LOW" if risk_score < 30 else ("MEDIUM" if risk_score < 65 else "HIGH")
    if _has_returns:
        st.metric("Risk Score", f"{risk_score} / 100", _risk_delta)
    else:
        st.metric("Risk Score", "Pending sim", "No history")

with k5:
    _alert_count = len(alerts)
    _alert_label = "All Clear" if _alert_count == 0 else f"{_alert_count} Active"
    st.metric("Alerts", _alert_label)

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ── Live market strip ─────────────────────────────────────────────────────────

_mkt = _market_overview()
_mkt_cols = st.columns(len(_PULSE_SYMS))
for _ci, _tkr in enumerate(_PULSE_SYMS):
    if not _mkt.empty and _tkr in _mkt.index:
        _row = _mkt.loc[_tkr]
        _price_str = f"${_row['price']:,.0f}" if _row["price"] >= 1000 else f"${_row['price']:,.2f}"
        _delta_str = f"{_row['pct_change']:+.2f}%"
        _mkt_cols[_ci].metric(_tkr, _price_str, _delta_str)
    else:
        _mkt_cols[_ci].metric(_tkr, "—")

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# ROW 2 — MAIN CHARTS (65% equity/drawdown | 35% allocation)
# ═══════════════════════════════════════════════════════════════════════════════

# ── Portfolio Health ──────────────────────────────────────────────────────────
st.markdown('<p class="db-panel-title">Portfolio Health</p>', unsafe_allow_html=True)

def _sortino(rets, target=0.0):
    try:
        import numpy as np
        downside = rets[rets < target]
        if len(downside) < 2: return 0.0
        return float((rets.mean() - target) / (downside.std() + 1e-9) * (252**0.5))
    except Exception: return 0.0

def _var95(rets):
    try:
        import numpy as np
        return float(np.percentile(rets, 5))
    except Exception: return 0.0

def _cvar95(rets):
    try:
        import numpy as np
        threshold = np.percentile(rets, 5)
        tail = rets[rets <= threshold]
        return float(tail.mean()) if len(tail) > 0 else 0.0
    except Exception: return 0.0

def _beta_spy(rets):
    try:
        import yfinance as yf, numpy as np
        if len(rets) < 10: return None
        start = str(rets.index[0].date()) if hasattr(rets.index[0], 'date') else None
        end   = str(rets.index[-1].date()) if hasattr(rets.index[-1], 'date') else None
        if not start or not end: return None
        spy_raw = yf.download("SPY", start=start, end=end, auto_adjust=True, progress=False)
        spy_rets = spy_raw["Close"].squeeze().pct_change().dropna()
        common = rets.index.intersection(spy_rets.index)
        if len(common) < 10: return None
        cov = np.cov(rets.loc[common], spy_rets.loc[common])
        return float(cov[0,1] / (cov[1,1] + 1e-9))
    except Exception: return None

if len(returns) > 10 and len(equity) > 10:
    _sharpe_h = float((returns.mean() / (returns.std() + 1e-9)) * (252**0.5))
    _sortino_h = _sortino(returns)
    _vol_h = float(returns.std() * (252**0.5) * 100)
    _maxdd_h = float(drawdown.min() * 100) if len(drawdown) > 0 else 0.0
    _var_h = float(_var95(returns) * 100)
    _cvar_h = float(_cvar95(returns) * 100)
    _beta_h = _beta_spy(returns)
    _gross_exp = market_value / portfolio_equity * 100 if portfolio_equity > 0 else 0.0
    _cash_pct  = cash / portfolio_equity * 100 if portfolio_equity > 0 else 100.0

    def _hval(v, fmt, red_below=None, red_above=None, green_above=None):
        try:
            s = fmt.format(v)
            color = "#94A3B8"
            if red_below is not None and v < red_below: color = "#EF4444"
            elif red_above is not None and v > red_above: color = "#EF4444"
            elif green_above is not None and v > green_above: color = "#10B981"
            return f'<span style="color:{color};font-family:JetBrains Mono,monospace;font-size:0.82rem;font-weight:700;">{s}</span>'
        except: return '<span style="color:#475569;">—</span>'

    _health_rows = [
        ("Sharpe Ratio",      _hval(_sharpe_h,  "{:.2f}",  green_above=1.0, red_below=0.0),
         "Annualised Vol",    _hval(_vol_h,      "{:.1f}%", red_above=30.0)),
        ("Sortino Ratio",     _hval(_sortino_h,  "{:.2f}",  green_above=1.5, red_below=0.0),
         "Max Drawdown",      _hval(_maxdd_h,    "{:.1f}%", red_below=-15.0)),
        ("VaR 95%",           _hval(_var_h,      "{:.2f}%", red_below=-3.0),
         "CVaR 95%",          _hval(_cvar_h,     "{:.2f}%", red_below=-4.0)),
        ("Beta vs SPY",       _hval(_beta_h, "{:.2f}") if _beta_h is not None else '<span style="color:#475569;">—</span>',
         "Gross Exposure",    _hval(_gross_exp,  "{:.0f}%")),
        ("Cash Allocation",   _hval(_cash_pct,   "{:.0f}%"),
         "Net Exposure",      _hval(_gross_exp,  "{:.0f}%")),
    ]
else:
    _na = '<span style="color:#334155;font-family:JetBrains Mono,monospace;font-size:0.68rem;font-style:italic;letter-spacing:0.03em;">awaiting backtest</span>'
    _health_rows = [
        ("Sharpe Ratio", _na, "Annualised Vol", _na),
        ("Sortino Ratio", _na, "Max Drawdown", _na),
        ("VaR 95%", _na, "CVaR 95%", _na),
        ("Beta vs SPY", _na, "Gross Exposure", _na),
        ("Cash Allocation", _na, "Net Exposure", _na),
    ]

_h_html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0;">'
for lbl1, val1, lbl2, val2 in _health_rows:
    _h_html += f'''
        <div style="padding:7px 12px;border-bottom:1px solid rgba(255,255,255,0.04);">
            <div style="font-size:0.55rem;font-family:JetBrains Mono,monospace;color:#334155;
                text-transform:uppercase;letter-spacing:0.14em;margin-bottom:3px;">{lbl1}</div>
            {val1}
        </div>
        <div style="padding:7px 12px;border-bottom:1px solid rgba(255,255,255,0.04);
            border-left:1px solid rgba(255,255,255,0.04);">
            <div style="font-size:0.55rem;font-family:JetBrains Mono,monospace;color:#334155;
                text-transform:uppercase;letter-spacing:0.14em;margin-bottom:3px;">{lbl2}</div>
            {val2}
        </div>'''
_h_html += '</div>'

_ph_left, _ph_right = st.columns([1, 1])
with _ph_left:
    st.markdown(f'''<div style="background:rgba(13,20,33,0.80);border:1px solid rgba(245,158,11,0.12);
        border-radius:9px;overflow:hidden;">{_h_html}</div>''', unsafe_allow_html=True)
with _ph_right:
    # Exposure bar
    if len(equity) > 0 and portfolio_equity > 0:
        _exp_bars = [
            ("LONG",  _gross_exp,  "#10B981"),
            ("CASH",  _cash_pct,   "#F59E0B"),
        ]
        _bar_html = '<div style="padding:14px 16px;background:rgba(13,20,33,0.80);border:1px solid rgba(245,158,11,0.12);border-radius:9px;">'
        _bar_html += '<div style="font-family:JetBrains Mono,monospace;font-size:0.55rem;color:#334155;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:12px;">Portfolio Exposure</div>'
        for _lbl, _pct, _clr in _exp_bars:
            _pct_c = max(0.0, min(100.0, _pct))
            _bar_html += f'''<div style="margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
                    <span style="font-family:JetBrains Mono,monospace;font-size:0.62rem;color:#64748B;">{_lbl}</span>
                    <span style="font-family:JetBrains Mono,monospace;font-size:0.62rem;color:{_clr};font-weight:700;">{_pct_c:.0f}%</span>
                </div>
                <div style="background:rgba(255,255,255,0.06);border-radius:3px;height:6px;overflow:hidden;">
                    <div style="background:{_clr};width:{_pct_c}%;height:100%;border-radius:3px;transition:width 0.3s;"></div>
                </div></div>'''
        _bar_html += f'<div style="margin-top:14px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.05);font-family:JetBrains Mono,monospace;font-size:0.60rem;color:#475569;">Total Equity: <span style="color:#E2E8F0;font-weight:700;">${portfolio_equity:,.0f}</span></div>'
        _bar_html += '</div>'
        st.markdown(_bar_html, unsafe_allow_html=True)
    else:
        st.markdown('<div style="padding:14px 16px;background:rgba(13,20,33,0.80);border:1px solid rgba(245,158,11,0.10);border-radius:9px;color:#334155;font-family:JetBrains Mono,monospace;font-size:0.72rem;">Run Trading Sim to see exposure breakdown.</div>', unsafe_allow_html=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

chart_col, alloc_col = st.columns([1.9, 1.0])

with chart_col:
    st.markdown(
        '<p class="db-panel-title">Portfolio Equity &amp; Drawdown</p>',
        unsafe_allow_html=True,
    )
    if len(equity) > 1:
        _x = list(range(len(equity)))
        _cfg = plotly_config()
        _cfg.pop("xaxis", None)
        _cfg.pop("yaxis", None)
        fig_combo = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.68, 0.32], vertical_spacing=0.04,
            subplot_titles=("Equity Curve", "Underwater Drawdown"),
        )
        fig_combo.add_trace(
            go.Scatter(x=_x, y=equity.values, mode="lines", name="Equity",
                       line=dict(color=_GREEN, width=2),
                       fill="tozeroy", fillcolor="rgba(16,185,129,0.08)"),
            row=1, col=1,
        )
        if len(drawdown) > 0:
            fig_combo.add_trace(
                go.Scatter(x=_x, y=drawdown.values, mode="lines", name="Drawdown",
                           line=dict(color=_RED, width=1.5),
                           fill="tozeroy", fillcolor="rgba(239,68,68,0.12)"),
                row=2, col=1,
            )
        _cfg.pop("legend", None)
        fig_combo.update_layout(height=480, showlegend=True,
                                legend=dict(orientation="h", y=1.02), **_cfg)
        fig_combo.update_xaxes(gridcolor="rgba(100,116,139,0.10)", showgrid=True)
        fig_combo.update_yaxes(gridcolor="rgba(100,116,139,0.10)", showgrid=True)
        st.plotly_chart(fig_combo, use_container_width=True, config={"displayModeBar": False})
    else:
        # SPY sparkline as placeholder
        if not spy_df.empty:
            _close = spy_df["Close"].squeeze().dropna().tail(30)
            fig_spy = go.Figure(go.Scatter(
                x=_close.index, y=_close.values, mode="lines",
                line=dict(color=_AMBER, width=1.8),
                fill="tozeroy", fillcolor="rgba(245,158,11,0.06)",
            ))
            fig_spy.update_layout(
                title="SPY — 30-Day (awaiting portfolio data)",
                **plotly_config(height=480, margin=dict(l=10, r=10, t=44, b=10)),
            )
            st.plotly_chart(fig_spy, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Run Trading Sim or Backtest to see your equity curve here.")

with alloc_col:
    st.markdown(
        '<p class="db-panel-title">Portfolio Allocation</p>',
        unsafe_allow_html=True,
    )
    if not positions_df.empty:
        _alloc = positions_df[["Ticker", "Weight %"]].sort_values("Weight %", ascending=False)
        _palette = [_GREEN, "#3b82f6", _AMBER, _RED, "#8b5cf6",
                    _CYAN, "#ec4899", "#a3e635", "#fb923c", "#94a3b8"]
        fig_donut = go.Figure(go.Pie(
            labels=_alloc["Ticker"],
            values=_alloc["Weight %"],
            hole=0.58,
            textinfo="label+percent",
            textfont=dict(size=11, color="#e2e8f0"),
            marker=dict(colors=_palette[:len(_alloc)], line=dict(color="#0a0f1a", width=2)),
        ))
        fig_donut.update_layout(
            annotations=[dict(text="Holdings", x=0.5, y=0.5,
                              font=dict(size=12, color="#94a3b8"), showarrow=False)],
            **plotly_config(height=480, margin=dict(l=10, r=10, t=20, b=10)),
        )
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

        # Compact allocation table below donut
        _show = positions_df[["Ticker", "Market Value", "Weight %"]].copy()
        _show["Market Value"] = _show["Market Value"].map(lambda x: f"${x:,.0f}")
        _show["Weight %"] = _show["Weight %"].map(lambda x: f"{x:.1f}%")
        st.dataframe(_show, use_container_width=True, hide_index=True)
    else:
        st.markdown(
            f"""
            <div style="
                display:flex; flex-direction:column; align-items:center;
                justify-content:center; height:300px; color:#475569;
                font-family:'JetBrains Mono',monospace; font-size:0.8rem;
                text-align:center; gap:12px;
            ">
                <div style="font-size:2rem">◎</div>
                <div>No positions open</div>
                <div style="font-size:0.7rem; color:#334155">Run Trading Sim to build a portfolio</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# ROW 3 — MARKET NEWS | BOT SIGNALS | RECENT TRADES
# ═══════════════════════════════════════════════════════════════════════════════

news_col, signal_col, trades_col = st.columns([1.4, 1.0, 1.2])

# ── News feed ─────────────────────────────────────────────────────────────────
with news_col:
    st.markdown('<p class="db-panel-title">Market News</p>', unsafe_allow_html=True)
    _news = _fetch_news("stock market investing")
    if _news:
        for item in _news:
            _title = str(item.get("title", ""))[:90]
            _src = str(item.get("source", "")).split(" - ")[-1][:28]
            _pub = str(item.get("published", ""))[:16]
            _link = str(item.get("link", "#"))
            st.markdown(
                f"""
                <div class="news-item">
                    <a class="news-headline" href="{_link}" target="_blank">{_title}</a>
                    <div class="news-meta">{_src} &nbsp;·&nbsp; {_pub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.caption("News feed temporarily unavailable.")

# ── Bot signals ───────────────────────────────────────────────────────────────
with signal_col:
    st.markdown('<p class="db-panel-title">System Signals</p>', unsafe_allow_html=True)

    # Primary bot signal chip
    _sig_lower = str(bot_signal).lower()
    if _sig_lower == "buy":
        _chip_cls = "signal-chip signal-buy"
        _sig_icon = "▲"
    elif _sig_lower == "sell":
        _chip_cls = "signal-chip signal-sell"
        _sig_icon = "▼"
    else:
        _chip_cls = "signal-chip signal-hold"
        _sig_icon = "◆"

    st.markdown(
        f'<span class="{_chip_cls}">{_sig_icon} BOT: {str(bot_signal).upper()}</span>',
        unsafe_allow_html=True,
    )
    st.caption(bot_reason[:120])
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Regime signal
    _reg_chip = "signal-buy" if regime_label in ("Bull",) else (
        "signal-sell" if regime_label in ("Bear", "Stress") else "signal-hold"
    )
    st.markdown(
        f'<span class="signal-chip {_reg_chip}">REGIME: {regime_label.upper()}</span>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Risk score bar
    _bar_color = _GREEN if risk_score < 30 else (_AMBER if risk_score < 65 else _RED)
    st.markdown(
        f"""
        <div style="margin-top:8px">
            <div style="font-family:'JetBrains Mono',monospace; font-size:0.65rem;
                        color:#94A3B8; text-transform:uppercase; letter-spacing:0.1em;
                        margin-bottom:4px;">Risk Score</div>
            <div class="risk-score-bar">
                <div class="risk-score-fill"
                     style="width:{risk_score}%; background:{_bar_color};"></div>
            </div>
            <div style="font-family:'JetBrains Mono',monospace; font-size:0.75rem;
                        color:{_bar_color}; margin-top:4px;">{risk_score}/100 — {_risk_delta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Alert list (compact)
    if alerts:
        for level, msg in alerts[:4]:
            _acls = "signal-sell" if level == "Critical" else (
                "signal-hold" if level == "Warning" else "signal-buy"
            )
            st.markdown(
                f'<div class="signal-chip {_acls}" style="margin-bottom:5px;display:block;font-size:0.65rem;">'
                f'{level.upper()}: {msg[:55]}{"…" if len(msg)>55 else ""}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<span class="signal-chip signal-buy">ALL CLEAR — No active alerts</span>',
            unsafe_allow_html=True,
        )

# ── Recent trades ─────────────────────────────────────────────────────────────
with trades_col:
    st.markdown('<p class="db-panel-title">Recent Trades</p>', unsafe_allow_html=True)
    if trades:
        trade_rows = [
            {
                "Time": datetime.fromtimestamp(t["ts"]).strftime("%m/%d %H:%M"),
                "Ticker": str(t["symbol"]).upper(),
                "Side": str(t["side"]).upper(),
                "Qty": int(float(t["qty"])),
                "Price": f"${float(t['price']):.2f}",
            }
            for t in trades
        ]
        trade_df = pd.DataFrame(trade_rows)
        st.dataframe(trade_df, use_container_width=True, hide_index=True)
    else:
        st.markdown(
            '<div style="padding:12px 0;font-family:\'JetBrains Mono\',monospace;'
            'font-size:0.72rem;color:#334155;font-style:italic;">'
            'No trades recorded — open Trading Sim to place your first order.'
            '</div>',
            unsafe_allow_html=True,
        )

    # Quick stats below trades
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    _ts1, _ts2 = st.columns(2)
    _ts1.metric("Sharpe", f"{sharpe:.2f}" if _has_returns else "—")
    _ts2.metric("Max DD", format_pct(max_drawdown) if _has_equity_history else "—")

st.divider()

# ─── Next step guidance ────────────────────────────────────────────────────────

st.divider()
nav_hub()

if kill_switch:
    next_step("Kill switch is ACTIVE. Open Risk Engine immediately to review and reset risk limits before placing new trades.")
elif len(positions_df) == 0 and len(equity) == 0:
    next_step("Start with Trading Sim to open positions and build portfolio history — all analytics populate from there.")
elif len(equity) < 5:
    next_step("Keep running Trading Sim — more trade history unlocks the full Risk Engine, Monte Carlo, and Strategy DNA analysis.")
elif len(alerts) > 0:
    next_step("Active alerts detected. Review Risk Engine and Alerts pages to understand and resolve portfolio risk.")
else:
    next_step("Portfolio is healthy. Explore Monte Carlo for scenario analysis, Portfolio Optimizer for allocation, or Strategy DNA for behavioral insights.")
