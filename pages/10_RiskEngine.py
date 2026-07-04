import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf

from components.layout import setup_page, section, next_step, plotly_config


# =============================
# Page setup
# =============================
setup_page(
    "Real-Time Risk Engine + Kill Switch",
    "Monitor drawdown, volatility, Sharpe ratio, worst-period loss, and automated risk-limit breaches.",
    "🛡️"
)


# =============================
# Load shared portfolio data
# =============================
strategy_returns = st.session_state.get("strategy_returns", None)
equity = st.session_state.get("equity_curve", None)
initial_capital = st.session_state.get("initial_capital", 100000.0)

_has_sim = (
    strategy_returns is not None
    and equity is not None
    and len(equity) >= 2
)

if not _has_sim:
    st.info("No simulation data yet. Run **Trading Sim** or **Backtest** to populate portfolio analytics.")

    @st.cache_data(ttl=300)
    def _re_fallback_mkt():
        try:
            from market.prices import fetch_latest_prices
            return fetch_latest_prices(["SPY", "QQQ", "IWM", "^VIX"], period="5d", interval="1d")
        except Exception:
            return pd.DataFrame()

    from components.layout import section
    section("Market Overview", "Live benchmark data while waiting for simulation results.")
    _fb = _re_fallback_mkt()
    if not _fb.empty:
        _fb_cols = st.columns(len(_fb))
        for _fc, (_tkr, _row) in zip(_fb_cols, _fb.iterrows()):
            _price_str = f"${_row['price']:,.2f}" if _row["price"] < 1000 else f"${_row['price']:,.0f}"
            _fc.metric(_tkr, _price_str, f"{_row['pct_change']:+.2f}%")
    st.page_link("pages/5_Trading_Sim.py", label="→ Go to Trading Sim", icon="💹")
    st.stop()

returns = pd.Series(strategy_returns).dropna()
equity = pd.Series(equity).dropna()

if len(equity) < 2 or len(returns) == 0:
    st.warning("Not enough trading history yet. Place a few trades first.")
    st.stop()


# =============================
# Risk Metrics
# =============================
drawdown = equity / equity.cummax() - 1

max_dd = float(drawdown.min())
current_drawdown = float(drawdown.iloc[-1])
volatility = float(returns.std())
annualized_volatility = float(returns.std() * np.sqrt(252))
sharpe = float((returns.mean() / (returns.std() + 1e-9)) * np.sqrt(252))
worst_period_return = float(returns.min())
total_return = float((equity.iloc[-1] / initial_capital) - 1)


# =============================
# Sidebar Risk Limits
# =============================
st.sidebar.header("Risk Limits")

max_dd_limit = st.sidebar.slider(
    "Max Drawdown Limit (%)",
    -50,
    0,
    -10
) / 100

loss_limit = st.sidebar.slider(
    "Worst Period Loss Limit (%)",
    -20,
    0,
    -5
) / 100

vol_limit = st.sidebar.slider(
    "Volatility Limit",
    0.0,
    0.2,
    0.05
)


# =============================
# Kill Switch Logic
# =============================
kill_switch = False
reasons = []

if max_dd < max_dd_limit:
    kill_switch = True
    reasons.append(f"Max drawdown exceeded: {max_dd * 100:.2f}%")

if worst_period_return < loss_limit:
    kill_switch = True
    reasons.append(f"Worst period loss exceeded: {worst_period_return * 100:.2f}%")

if volatility > vol_limit:
    kill_switch = True
    reasons.append(f"Volatility too high: {volatility:.4f}")

st.session_state["kill_switch"] = kill_switch
st.session_state["kill_switch_reasons"] = reasons


# =============================
# Risk Status
# =============================
section("Risk Status", "Current system state based on selected risk limits.")

if kill_switch:
    st.error("KILL SWITCH ACTIVATED")

    i = 0
    while i < len(reasons):
        st.write(f"- {reasons[i]}")
        i += 1

else:
    st.success("All systems normal. No risk limits are currently breached.")

st.divider()


# =============================
# Metrics
# =============================
section("Risk Metrics", "Core portfolio risk and performance statistics.")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Max Drawdown", f"{max_dd * 100:.2f}%")
c2.metric("Current Drawdown", f"{current_drawdown * 100:.2f}%")
c3.metric("Volatility", f"{volatility:.4f}")
c4.metric("Sharpe Ratio", f"{sharpe:.2f}")
c5.metric("Total Return", f"{total_return * 100:.2f}%")

c6, c7, c8 = st.columns(3)

c6.metric("Worst Period Return", f"{worst_period_return * 100:.2f}%")
c7.metric("Annualized Volatility", f"{annualized_volatility * 100:.2f}%")
c8.metric("Risk Limits Breached", f"{len(reasons)}")

st.divider()


# =============================
# Risk insight
# =============================
section("Risk Insight", "Plain-English interpretation of the current portfolio risk state.")

if kill_switch:
    st.error("Risk limits are breached. Trading should remain disabled until the issue is reviewed.")

elif max_dd < -0.10:
    st.warning("Drawdown is meaningful. Monitor the portfolio before increasing exposure.")

elif volatility > vol_limit * 0.75:
    st.warning("Volatility is approaching the selected risk limit.")

elif sharpe > 1:
    st.success("Risk-adjusted performance is currently strong.")

else:
    st.info("Portfolio risk is currently within selected limits.")

st.divider()


# =============================
# Charts
# =============================
section("Equity Curve", "Portfolio value over time.")

fig_eq = go.Figure(go.Scatter(
    x=list(range(len(equity))),
    y=equity.values,
    mode="lines",
    name="Equity",
    line=dict(color="#10b981", width=2)
))
fig_eq.update_layout(title="Equity Curve", xaxis_title="Period", yaxis_title="Portfolio Value", **plotly_config())
st.plotly_chart(fig_eq, use_container_width=True)

st.divider()

section("Drawdown Curve", "Peak-to-trough decline over time.")

fig_dd = go.Figure(go.Scatter(
    x=list(range(len(drawdown))),
    y=drawdown.values,
    mode="lines",
    name="Drawdown",
    line=dict(color="#ef4444", width=2)
))
fig_dd.update_layout(title="Drawdown Curve", xaxis_title="Period", yaxis_title="Drawdown", **plotly_config())
st.plotly_chart(fig_dd, use_container_width=True)

st.divider()


# =============================
# Rolling Volatility
# =============================
section("Rolling Volatility (21-day)", "Annualised 21-day rolling volatility vs the selected limit.")

_roll_vol = returns.rolling(21).std() * np.sqrt(252)

fig_rv = go.Figure(go.Scatter(
    x=list(range(len(_roll_vol))), y=_roll_vol.values,
    mode="lines", name="Rolling Vol (21d)",
    line=dict(color="#f59e0b", width=2),
    fill="tozeroy", fillcolor="rgba(245,158,11,0.07)",
))
fig_rv.add_hline(y=vol_limit * np.sqrt(252), line_dash="dash", line_color="#ef4444", line_width=1,
                 annotation_text=f"Limit: {vol_limit * np.sqrt(252):.2%}",
                 annotation_position="top right",
                 annotation_font_color="#ef4444")
fig_rv.update_layout(title="21-Day Rolling Annualised Volatility",
                     xaxis_title="Period", yaxis_title="Ann. Volatility",
                     **plotly_config())
st.plotly_chart(fig_rv, use_container_width=True)

st.divider()


# =============================
# Risk Gauges
# =============================
section("Risk Gauge Dashboard", "At-a-glance gauge indicators for key risk metrics.")

_var_95 = float(np.percentile(returns, 5))
_dd_pct = abs(max_dd) * 100
_gauge_layout = plotly_config(height=260, margin=dict(l=20, r=20, t=60, b=20))

_rg1, _rg2, _rg3 = st.columns(3)

with _rg1:
    fig_g1 = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=sharpe,
        title=dict(text="Sharpe Ratio", font=dict(color="#e2e8f0", size=14)),
        delta=dict(reference=1.0, relative=False, valueformat=".2f"),
        gauge=dict(
            axis=dict(range=[-2, 3], tickcolor="#64748b", tickfont=dict(color="#94a3b8")),
            bar=dict(color="#10b981"),
            bgcolor="rgba(30,41,59,0.6)",
            steps=[
                dict(range=[-2, 0],  color="rgba(239,68,68,0.18)"),
                dict(range=[0,  1],  color="rgba(245,158,11,0.14)"),
                dict(range=[1,  3],  color="rgba(16,185,129,0.14)"),
            ],
            threshold=dict(line=dict(color="#10b981", width=2), thickness=0.75, value=1),
        ),
        number=dict(font=dict(color="#f1f5f9", size=28), valueformat=".2f"),
    ))
    fig_g1.update_layout(**_gauge_layout)
    st.plotly_chart(fig_g1, use_container_width=True)

with _rg2:
    fig_g2 = go.Figure(go.Indicator(
        mode="gauge+number",
        value=abs(_var_95) * 100,
        title=dict(text="1-Day VaR 95% (%)", font=dict(color="#e2e8f0", size=14)),
        gauge=dict(
            axis=dict(range=[0, 10], tickcolor="#64748b", tickfont=dict(color="#94a3b8")),
            bar=dict(color="#ef4444"),
            bgcolor="rgba(30,41,59,0.6)",
            steps=[
                dict(range=[0, 2],  color="rgba(16,185,129,0.14)"),
                dict(range=[2, 5],  color="rgba(245,158,11,0.14)"),
                dict(range=[5, 10], color="rgba(239,68,68,0.18)"),
            ],
        ),
        number=dict(font=dict(color="#f1f5f9", size=28), valueformat=".2f", suffix="%"),
    ))
    fig_g2.update_layout(**_gauge_layout)
    st.plotly_chart(fig_g2, use_container_width=True)

with _rg3:
    fig_g3 = go.Figure(go.Indicator(
        mode="gauge+number",
        value=_dd_pct,
        title=dict(text="Max Drawdown (%)", font=dict(color="#e2e8f0", size=14)),
        gauge=dict(
            axis=dict(range=[0, 50], tickcolor="#64748b", tickfont=dict(color="#94a3b8")),
            bar=dict(color="#8b5cf6"),
            bgcolor="rgba(30,41,59,0.6)",
            steps=[
                dict(range=[0,  10], color="rgba(16,185,129,0.14)"),
                dict(range=[10, 25], color="rgba(245,158,11,0.14)"),
                dict(range=[25, 50], color="rgba(239,68,68,0.18)"),
            ],
            threshold=dict(line=dict(color="#ef4444", width=2), thickness=0.75,
                           value=abs(max_dd_limit) * 100),
        ),
        number=dict(font=dict(color="#f1f5f9", size=28), valueformat=".2f", suffix="%"),
    ))
    fig_g3.update_layout(**_gauge_layout)
    st.plotly_chart(fig_g3, use_container_width=True)

st.divider()


# =============================
# Holdings Correlation Heatmap
# =============================
section("Holdings Correlation (60-day)", "Recent 60-day return correlations across current positions.")

try:
    from execution.sim_broker import get_positions as _get_pos
    _pos_list = _get_pos()
    _tickers = [str(p["symbol"]).upper() for p in _pos_list if float(p.get("qty", 0)) > 0]

    if len(_tickers) >= 2:
        @st.cache_data(ttl=3600)
        def _load_corr_prices(tickers_key):
            _raw = yf.download(list(tickers_key), period="60d", interval="1d",
                               auto_adjust=True, progress=False)
            if _raw.empty:
                return pd.DataFrame()
            if isinstance(_raw.columns, pd.MultiIndex):
                if "Close" in _raw.columns.get_level_values(0):
                    return _raw["Close"].dropna()
            return _raw[["Close"]].rename(columns={"Close": list(tickers_key)[0]}).dropna()

        _corr_prices = _load_corr_prices(tuple(sorted(_tickers)))

        if not _corr_prices.empty and _corr_prices.shape[1] >= 2:
            _corr = _corr_prices.pct_change().dropna().corr()
            _labels = _corr.columns.tolist()
            fig_corr = go.Figure(go.Heatmap(
                z=_corr.values.tolist(),
                x=_labels, y=_labels,
                colorscale="RdYlGn",
                zmid=0, zmin=-1, zmax=1,
                text=[[f"{v:.2f}" for v in row] for row in _corr.values],
                texttemplate="%{text}",
                colorbar=dict(title="ρ", thickness=14, tickfont=dict(color="#e2e8f0")),
            ))
            fig_corr.update_layout(
                title="60-Day Holdings Return Correlation",
                **plotly_config(margin=dict(l=10, r=10, t=44, b=10)),
            )
            st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.info("Not enough overlapping price data to compute correlations.")
    else:
        st.info("Open at least 2 positions in Trading Sim to see the correlation heatmap.")

except Exception:
    st.info("Correlation heatmap requires open positions from Trading Sim.")

st.divider()


# =============================
# Risk Table
# =============================
section("Risk Data", "Raw equity and drawdown values used by the risk engine.")

risk_df = pd.DataFrame({
    "Equity": equity,
    "Drawdown": drawdown
})

st.dataframe(
    risk_df,
    use_container_width=True
)


# =============================
# Next step
# =============================
if kill_switch:
    next_step("Go to Trading Sim only after reviewing the breached risk limits. Consider reducing exposure or resetting the simulated account.")
else:
    next_step("Use Monte Carlo or Alerts next to forecast future risk and monitor possible portfolio breaches.")
