import streamlit as st
import pandas as pd
import numpy as np

from components.layout import setup_page, section, next_step


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

if strategy_returns is None or equity is None or len(equity) == 0:
    st.warning("No trading simulation data found. Run the Trading Sim or Performance page first.")
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

st.line_chart(equity)

st.divider()

section("Drawdown Curve", "Peak-to-trough decline over time.")

st.line_chart(drawdown)

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