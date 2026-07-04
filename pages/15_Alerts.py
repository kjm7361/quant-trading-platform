import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from components.layout import setup_page, section, next_step, plotly_config


# =============================
# Page setup
# =============================
setup_page(
    "Real-Time Alerts + Signal Engine",
    "Monitor portfolio risk, return, volatility, profit targets, and kill-switch alerts in one place.",
    "🚨"
)


# =============================
# Helpers
# =============================
def safe_series(x):
    if x is None:
        return pd.Series(dtype=float)

    return pd.Series(x).dropna()


def compute_drawdown(equity):
    equity = safe_series(equity)

    if len(equity) == 0:
        return pd.Series(dtype=float)

    return equity / equity.cummax() - 1


# =============================
# Load shared portfolio state
# =============================
strategy_returns = st.session_state.get("strategy_returns", None)
equity_curve = st.session_state.get("equity_curve", None)
kill_switch = st.session_state.get("kill_switch", False)
kill_switch_reasons = st.session_state.get("kill_switch_reasons", [])

returns = safe_series(strategy_returns)
equity = safe_series(equity_curve)

if len(equity) == 0:
    st.info("No simulation data yet. Run **Trading Sim** or **Backtest** to populate portfolio analytics.")

    @st.cache_data(ttl=300)
    def _al_fallback_mkt():
        try:
            from market.prices import fetch_latest_prices
            return fetch_latest_prices(["SPY", "QQQ", "IWM", "^VIX"], period="5d", interval="1d")
        except Exception:
            return pd.DataFrame()

    from components.layout import section
    section("Market Overview", "Live benchmark data while waiting for simulation results.")
    _fb = _al_fallback_mkt()
    if not _fb.empty:
        _fb_cols = st.columns(len(_fb))
        for _fc, (_tkr, _row) in zip(_fb_cols, _fb.iterrows()):
            _price_str = f"${_row['price']:,.2f}" if _row["price"] < 1000 else f"${_row['price']:,.0f}"
            _fc.metric(_tkr, _price_str, f"{_row['pct_change']:+.2f}%")
    st.page_link("pages/5_Trading_Sim.py", label="→ Go to Trading Sim", icon="💹")
    st.stop()

drawdown = compute_drawdown(equity)

if len(returns) == 0 and len(equity) >= 2:
    returns = equity.pct_change().dropna()


# =============================
# Sidebar alert rules
# =============================
st.sidebar.header("Alert Rules")

drawdown_limit = st.sidebar.slider(
    "Drawdown Alert (%)",
    -50,
    0,
    -10
) / 100

vol_limit = st.sidebar.slider(
    "Volatility Alert",
    0.0,
    0.2,
    0.05
)

loss_limit = st.sidebar.slider(
    "Worst Period Loss Alert (%)",
    -20,
    0,
    -5
) / 100

profit_target = st.sidebar.slider(
    "Profit Target Alert (%)",
    0,
    100,
    10
) / 100

rolling_window = st.sidebar.slider(
    "Rolling Window",
    3,
    60,
    20
)


# =============================
# Compute alert metrics
# =============================
alerts = []

latest_equity = float(equity.iloc[-1]) if len(equity) > 0 else 0.0
latest_drawdown = float(drawdown.iloc[-1]) if len(drawdown) > 0 else 0.0
max_drawdown = float(drawdown.min()) if len(drawdown) > 0 else 0.0

total_return = (
    float((equity.iloc[-1] / equity.iloc[0]) - 1)
    if len(equity) > 1
    else 0.0
)

if len(returns) > 0:
    latest_return = float(returns.iloc[-1])
    realized_vol = float(returns.std())

    if len(returns) >= rolling_window:
        rolling_vol = float(returns.tail(rolling_window).std())
    else:
        rolling_vol = float(returns.std())

    avg_return = float(returns.mean())

else:
    latest_return = 0.0
    realized_vol = 0.0
    rolling_vol = 0.0
    avg_return = 0.0


# =============================
# Alert logic
# =============================
if latest_drawdown < drawdown_limit:
    alerts.append({
        "level": "Critical",
        "message": f"Current drawdown breached alert limit: {latest_drawdown*100:.2f}%"
    })

if max_drawdown < drawdown_limit:
    alerts.append({
        "level": "Warning",
        "message": f"Historical max drawdown is beyond limit: {max_drawdown*100:.2f}%"
    })

if latest_return < loss_limit:
    alerts.append({
        "level": "Critical",
        "message": f"Latest period return breached loss alert: {latest_return*100:.2f}%"
    })

if rolling_vol > vol_limit:
    alerts.append({
        "level": "Warning",
        "message": f"Rolling volatility is elevated: {rolling_vol:.4f}"
    })

if total_return > profit_target:
    alerts.append({
        "level": "Positive",
        "message": f"Portfolio profit target reached: {total_return*100:.2f}%"
    })

if avg_return < 0:
    alerts.append({
        "level": "Warning",
        "message": f"Average return is negative over the observed sample: {avg_return*100:.4f}%"
    })

if kill_switch:
    reason_text = (
        "; ".join(kill_switch_reasons)
        if len(kill_switch_reasons) > 0
        else "Risk limits exceeded"
    )

    alerts.append({
        "level": "Critical",
        "message": f"Kill switch is active: {reason_text}"
    })


# =============================
# System status
# =============================
if len(alerts) == 0:
    system_status = "Normal"

elif any(a["level"] == "Critical" for a in alerts):
    system_status = "Critical"

elif any(a["level"] == "Warning" for a in alerts):
    system_status = "Warning"

else:
    system_status = "Positive"


# =============================
# System status display
# =============================
section(
    "System Status",
    "Current alert state based on portfolio performance and risk thresholds."
)

if system_status == "Normal":
    st.success("🟢 Normal")

elif system_status == "Warning":
    st.warning("🟡 Warning")

elif system_status == "Critical":
    st.error("🔴 Critical")

else:
    st.info("🔵 Positive")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Portfolio Equity", f"${latest_equity:,.2f}")
c2.metric("Current Drawdown", f"{latest_drawdown*100:.2f}%")
c3.metric("Max Drawdown", f"{max_drawdown*100:.2f}%")
c4.metric("Rolling Volatility", f"{rolling_vol:.4f}")
c5.metric("Total Return", f"{total_return*100:.2f}%")

st.divider()


# =============================
# Alert feed
# =============================
section(
    "Alert Feed",
    "Live list of currently triggered alert conditions."
)

if len(alerts) == 0:
    st.success("No active alerts.")

else:
    i = 0

    while i < len(alerts):
        level = alerts[i]["level"]
        msg = alerts[i]["message"]

        if level == "Critical":
            st.error(f"[{level}] {msg}")

        elif level == "Warning":
            st.warning(f"[{level}] {msg}")

        elif level == "Positive":
            st.success(f"[{level}] {msg}")

        else:
            st.info(f"[{level}] {msg}")

        i += 1

st.divider()


# =============================
# Monitoring charts
# =============================
section(
    "Monitoring Charts",
    "Portfolio equity, drawdown, and rolling volatility monitoring."
)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=list(range(len(equity))),
    y=equity.values.tolist(),
    mode="lines",
    name="Equity",
    line=dict(color="#10b981", width=2)
))

if len(drawdown) > 0:
    fig.add_trace(go.Scatter(
        x=list(range(len(drawdown))),
        y=drawdown.values.tolist(),
        mode="lines",
        name="Drawdown",
        line=dict(color="#ef4444", width=2)
    ))

fig.update_layout(title="Portfolio Monitoring", xaxis_title="Period", yaxis_title="Value", **plotly_config())
st.plotly_chart(fig, use_container_width=True)

if len(returns) > 0:
    vol_series = returns.rolling(rolling_window).std().dropna()

    if len(vol_series) > 0:
        st.divider()

        section(
            "Rolling Volatility",
            "Recent realized volatility over the selected rolling window."
        )

        fig_vol = go.Figure(go.Scatter(
            x=list(range(len(vol_series))),
            y=vol_series.values.tolist(),
            mode="lines",
            name="Rolling Volatility",
            line=dict(color="#f59e0b", width=2)
        ))
        fig_vol.update_layout(title="Rolling Volatility", xaxis_title="Period", yaxis_title="Volatility", **plotly_config())
        st.plotly_chart(fig_vol, use_container_width=True)

st.divider()


# =============================
# Alert summary table
# =============================
section(
    "Alert Summary Table",
    "Current metric values compared with configured alert thresholds."
)

summary_rows = [
    {
        "Metric": "Current Drawdown",
        "Value": f"{latest_drawdown*100:.2f}%",
        "Threshold": f"{drawdown_limit*100:.2f}%"
    },
    {
        "Metric": "Max Drawdown",
        "Value": f"{max_drawdown*100:.2f}%",
        "Threshold": f"{drawdown_limit*100:.2f}%"
    },
    {
        "Metric": "Latest Period Return",
        "Value": f"{latest_return*100:.2f}%",
        "Threshold": f"{loss_limit*100:.2f}%"
    },
    {
        "Metric": "Rolling Volatility",
        "Value": f"{rolling_vol:.4f}",
        "Threshold": f"{vol_limit:.4f}"
    },
    {
        "Metric": "Total Return",
        "Value": f"{total_return*100:.2f}%",
        "Threshold": f"{profit_target*100:.2f}%"
    }
]

st.dataframe(
    pd.DataFrame(summary_rows),
    use_container_width=True
)

st.divider()


# =============================
# Alert insight
# =============================
section(
    "Alert Insight",
    "Plain-English recommended action based on the current system status."
)

if system_status == "Critical":
    st.error("Consider reducing exposure, reviewing the Risk Engine, and pausing new trades.")

elif system_status == "Warning":
    st.warning("Monitor the portfolio closely and review recent changes in volatility or drawdown.")

elif system_status == "Positive":
    st.success("Portfolio performance is above the selected target. Review whether to lock in gains or keep risk constant.")

else:
    st.info("System is operating normally. Continue monitoring Trading Sim, Risk Engine, and Monte Carlo.")


# =============================
# Next step
# =============================
if system_status == "Critical":
    next_step("Open Risk Engine or Trading Sim next to review breached limits and reduce portfolio risk.")
else:
    next_step("Use Monte Carlo or Strategy DNA next to understand whether current alerts are likely to persist.")
