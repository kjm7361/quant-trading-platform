import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from components.layout import setup_page, section, next_step, plotly_config


# =============================
# Page setup
# =============================
setup_page(
    "Monte Carlo Portfolio Simulation",
    "Simulate thousands of possible future portfolio paths using your historical strategy returns.",
    "🎲"
)


# =============================
# Load shared portfolio data
# =============================
strategy_returns = st.session_state.get("strategy_returns", None)
equity_curve = st.session_state.get("equity_curve", None)
initial_capital = st.session_state.get("initial_capital", 100000.0)

_has_sim = (
    strategy_returns is not None
    and equity_curve is not None
    and len(equity_curve) >= 2
)

if not _has_sim:
    st.info("No simulation data yet. Run **Trading Sim** or **Backtest** to populate portfolio analytics.")

    @st.cache_data(ttl=300)
    def _mc_fallback_mkt():
        try:
            from market.prices import fetch_latest_prices
            return fetch_latest_prices(["SPY", "QQQ", "IWM", "^VIX"], period="5d", interval="1d")
        except Exception:
            return pd.DataFrame()

    from components.layout import section
    section("Market Overview", "Live benchmark data while waiting for simulation results.")
    _fb = _mc_fallback_mkt()
    if not _fb.empty:
        _fb_cols = st.columns(len(_fb))
        for _fc, (_tkr, _row) in zip(_fb_cols, _fb.iterrows()):
            _price_str = f"${_row['price']:,.2f}" if _row["price"] < 1000 else f"${_row['price']:,.0f}"
            _fc.metric(_tkr, _price_str, f"{_row['pct_change']:+.2f}%")
    st.page_link("pages/5_Trading_Sim.py", label="→ Go to Trading Sim", icon="💹")
    st.stop()

returns = pd.Series(strategy_returns).dropna()
equity = pd.Series(equity_curve).dropna()

if len(returns) < 2:
    st.warning("Not enough return history yet. Place a few trades or run a backtest first.")
    st.stop()


# =============================
# Sidebar settings
# =============================
st.sidebar.header("Simulation Settings")

num_simulations = st.sidebar.slider(
    "Number of Simulations",
    100,
    5000,
    1000,
    100
)

forecast_days = st.sidebar.slider(
    "Forecast Horizon Days",
    5,
    252,
    60,
    5
)

use_drift = st.sidebar.checkbox(
    "Use Historical Average Return",
    value=True
)

seed = st.sidebar.number_input(
    "Random Seed",
    min_value=0,
    value=42,
    step=1
)


# =============================
# Simulation
# =============================
np.random.seed(int(seed))

current_value = float(equity.iloc[-1])
mu = float(returns.mean()) if use_drift else 0.0
sigma = float(returns.std())

simulated_paths = np.zeros((forecast_days + 1, num_simulations))
simulated_paths[0, :] = current_value

i = 1
while i <= forecast_days:
    z = np.random.standard_normal(num_simulations)
    simulated_paths[i, :] = simulated_paths[i - 1, :] * (1 + mu + sigma * z)
    i += 1

ending_values = simulated_paths[-1, :]

prob_profit = float(np.mean(ending_values > current_value) * 100)
prob_loss = float(np.mean(ending_values < current_value) * 100)
mean_ending = float(np.mean(ending_values))
median_ending = float(np.median(ending_values))
p5 = float(np.percentile(ending_values, 5))
p95 = float(np.percentile(ending_values, 95))
expected_return = float((mean_ending / current_value) - 1)

var_5 = float(current_value - p5)
cvar_5 = float(current_value - np.mean(ending_values[ending_values <= p5])) if len(ending_values[ending_values <= p5]) > 0 else 0.0


# =============================
# Summary metrics
# =============================
section("Simulation Summary", "Forward-looking portfolio outcome estimates based on historical return behavior.")

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Current Portfolio", f"${current_value:,.2f}")
c2.metric("Mean Ending Value", f"${mean_ending:,.2f}")
c3.metric("Median Ending Value", f"${median_ending:,.2f}")
c4.metric("Prob. Profit", f"{prob_profit:.2f}%")
c5.metric("Prob. Loss", f"{prob_loss:.2f}%")
c6.metric("Expected Return", f"{expected_return*100:.2f}%")

c7, c8, c9, c10 = st.columns(4)

c7.metric("5th Percentile", f"${p5:,.2f}")
c8.metric("95th Percentile", f"${p95:,.2f}")
c9.metric("VaR 5%", f"${var_5:,.2f}")
c10.metric("CVaR 5%", f"${cvar_5:,.2f}")

st.divider()


# =============================
# Insight
# =============================
section("Risk Insight", "Plain-English interpretation of the simulation results.")

if prob_loss > 50:
    st.warning("More than half of the simulations end below the current portfolio value.")
elif p5 < current_value * 0.90:
    st.warning("The lower-tail outcome shows meaningful downside risk.")
elif prob_profit > 60:
    st.success("Most simulations end above the current portfolio value.")
else:
    st.info("The simulation shows a balanced range of possible future outcomes.")

st.divider()


# =============================
# Simulated paths
# =============================
section("Simulated Portfolio Paths", "A sample of possible future portfolio trajectories.")

paths_to_show = min(100, num_simulations)
x_days = list(range(forecast_days + 1))

color_palette = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"]

fig1 = go.Figure()
i = 0
while i < paths_to_show:
    fig1.add_trace(go.Scatter(
        x=x_days,
        y=simulated_paths[:, i].tolist(),
        mode="lines",
        line=dict(color=color_palette[i % len(color_palette)], width=1),
        opacity=0.35,
        showlegend=False
    ))
    i += 1

fig1.update_layout(title="Monte Carlo Simulated Paths", xaxis_title="Days", yaxis_title="Portfolio Value", **plotly_config())
st.plotly_chart(fig1, use_container_width=True)

st.divider()


# =============================
# Ending value distribution
# =============================
section("Ending Value Distribution", "Distribution of final portfolio values at the end of the forecast horizon.")

fig2 = go.Figure(go.Histogram(
    x=ending_values,
    nbinsx=40,
    marker_color="#10b981"
))

fig2.add_vline(x=current_value, line_dash="dash", line_color="#94a3b8", annotation_text="Current Value")
fig2.add_vline(x=p5, line_dash="dash", line_color="#ef4444", annotation_text="5th Percentile")
fig2.add_vline(x=p95, line_dash="dash", line_color="#3b82f6", annotation_text="95th Percentile")

fig2.update_layout(title="Distribution of Ending Values", xaxis_title="Ending Portfolio Value", yaxis_title="Frequency", **plotly_config())
st.plotly_chart(fig2, use_container_width=True)

st.divider()


# =============================
# Scenario table
# =============================
section("Simulation Details", "Detailed input assumptions and outcome statistics.")

summary_df = pd.DataFrame({
    "Metric": [
        "Current Portfolio Value",
        "Initial Capital",
        "Historical Mean Return",
        "Historical Volatility",
        "Forecast Horizon Days",
        "Number of Simulations",
        "Mean Ending Value",
        "Median Ending Value",
        "Probability of Profit",
        "Probability of Loss",
        "5th Percentile Outcome",
        "95th Percentile Outcome",
        "Value at Risk 5%",
        "Conditional VaR 5%"
    ],
    "Value": [
        f"${current_value:,.2f}",
        f"${float(initial_capital):,.2f}",
        f"{mu*100:.4f}%",
        f"{sigma*100:.4f}%",
        forecast_days,
        num_simulations,
        f"${mean_ending:,.2f}",
        f"${median_ending:,.2f}",
        f"{prob_profit:.2f}%",
        f"{prob_loss:.2f}%",
        f"${p5:,.2f}",
        f"${p95:,.2f}",
        f"${var_5:,.2f}",
        f"${cvar_5:,.2f}"
    ]
})

st.dataframe(
    summary_df,
    use_container_width=True
)


# =============================
# Next step
# =============================
next_step(
    "Use Risk Engine or Alerts next to turn this forecasted downside risk into active portfolio risk controls."
)
