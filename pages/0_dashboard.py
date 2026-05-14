import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from execution.sim_broker import get_cash, get_positions, list_trades
from components.layout import setup_page, section, next_step

setup_page(
    "Quant Trading Platform Dashboard",
    "A professional overview of portfolio health, risk, alerts, and system status.",
    "📊"
)

# -----------------------------
# Helpers
# -----------------------------
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

    i = 0
    while i < len(positions):
        p = positions[i]
        symbol = str(p["symbol"]).upper().strip()
        qty = float(p["qty"])
        avg_price = float(p["avg_price"])
        market_value = qty * avg_price

        total_market_value += market_value

        rows.append({
            "Ticker": symbol,
            "Qty": qty,
            "Avg Price": avg_price,
            "Market Value": market_value
        })
        i += 1

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
        latest_drawdown = 0.0
        max_drawdown = 0.0
        total_return = 0.0

    if len(returns) > 0:
        rolling_vol = float(returns.tail(min(20, len(returns))).std())
        latest_return = float(returns.iloc[-1])
    else:
        rolling_vol = 0.0
        latest_return = 0.0

    if latest_drawdown < -0.10:
        alerts.append(("Critical", f"Current drawdown is elevated at {format_pct(latest_drawdown)}"))
    if max_drawdown < -0.15:
        alerts.append(("Warning", f"Historical max drawdown reached {format_pct(max_drawdown)}"))
    if rolling_vol > 0.05:
        alerts.append(("Warning", f"Rolling volatility is high at {rolling_vol:.4f}"))
    if latest_return < -0.03:
        alerts.append(("Critical", f"Latest period return dropped to {format_pct(latest_return)}"))
    if total_return > 0.10:
        alerts.append(("Positive", f"Portfolio is above the 10% gain threshold at {format_pct(total_return)}"))
    if kill_switch:
        reason_text = "; ".join(kill_switch_reasons) if len(kill_switch_reasons) > 0 else "Risk limits exceeded"
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


# -----------------------------
# Load shared state
# -----------------------------
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
trades = list_trades(limit=10)
alerts = build_alerts(returns, equity, kill_switch, kill_switch_reasons)
system_status = get_status(kill_switch, alerts)

if len(returns) > 0:
    rolling_vol = float(returns.tail(min(20, len(returns))).std())
    sharpe = float((returns.mean() / (returns.std() + 1e-9)) * np.sqrt(252))
else:
    rolling_vol = 0.0
    sharpe = 0.0

if len(drawdown) > 0:
    max_drawdown = float(drawdown.min())
else:
    max_drawdown = 0.0

if len(equity) > 1:
    total_return = float((equity.iloc[-1] / equity.iloc[0]) - 1)
else:
    total_return = 0.0

if not positions_df.empty:
    largest_position = str(positions_df.iloc[0]["Ticker"])
    largest_weight = float(positions_df.iloc[0]["Weight"])
else:
    largest_position = "None"
    largest_weight = 0.0

# -----------------------------
# Status banner
# -----------------------------
if system_status == "Critical":
    st.error("System Status: Critical")
elif system_status == "Warning":
    st.warning("System Status: Warning")
elif system_status == "Positive":
    st.success("System Status: Positive")
else:
    st.info("System Status: Normal")

# -----------------------------
# Top metrics
# -----------------------------
section("Platform Overview", "Key portfolio, risk, and system metrics.")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Portfolio Equity", format_money(portfolio_equity))
c2.metric("Cash", format_money(cash))
c3.metric("Market Value", format_money(market_value))
c4.metric("Total Return", format_pct(total_return))
c5.metric("Max Drawdown", format_pct(max_drawdown))
c6.metric("Rolling Volatility", f"{rolling_vol:.4f}")

c7, c8, c9, c10, c11, c12 = st.columns(6)
c7.metric("Sharpe Ratio", f"{sharpe:.2f}")
c8.metric("Open Positions", f"{len(positions_df)}")
c9.metric("Largest Position", largest_position)
c10.metric("Largest Weight", format_pct(largest_weight))
c11.metric("Bot Signal", str(bot_signal).upper())
c12.metric("Kill Switch", "ACTIVE" if kill_switch else "OFF")

st.divider()

# -----------------------------
# Main layout
# -----------------------------
left, right = st.columns([2.2, 1.2])

with left:
    section("Portfolio Equity Curve")

    if len(equity) > 0:
        st.line_chart(equity)
    else:
        st.info("No equity history found yet. Use Trading Sim first.")

    section("Drawdown Profile")
    if len(drawdown) > 0:
        st.line_chart(drawdown)
    else:
        st.info("No drawdown data available yet.")

with right:
    section("System Alerts")

    if len(alerts) == 0:
        st.success("No active alerts.")
    else:
        i = 0
        while i < len(alerts):
            level, message = alerts[i]
            if level == "Critical":
                st.error(message)
            elif level == "Warning":
                st.warning(message)
            elif level == "Positive":
                st.success(message)
            else:
                st.info(message)
            i += 1

    section("Bot Insight")
    if str(bot_signal).lower() == "buy":
        st.success(f"Bot suggests BUY. {bot_reason}")
    elif str(bot_signal).lower() == "sell":
        st.error(f"Bot suggests SELL. {bot_reason}")
    elif str(bot_signal).lower() == "hold":
        st.info(f"Bot suggests HOLD. {bot_reason}")
    else:
        st.info(bot_reason)

st.divider()

# -----------------------------
# Positions and trades
# -----------------------------
pcol, tcol = st.columns(2)

with pcol:
    section("Current Positions")

    if positions_df.empty:
        st.info("No open positions.")
    else:
        show_positions = positions_df.copy()
        show_positions["Avg Price"] = show_positions["Avg Price"].map(lambda x: round(float(x), 2))
        show_positions["Market Value"] = show_positions["Market Value"].map(lambda x: round(float(x), 2))
        show_positions["Weight %"] = show_positions["Weight %"].map(lambda x: round(float(x), 2))
        st.dataframe(show_positions[["Ticker", "Qty", "Avg Price", "Market Value", "Weight %"]], use_container_width=True)

with tcol:
    section("Recent Trades")

    if len(trades) == 0:
        st.info("No recent trades.")
    else:
        trade_rows = []
        i = 0
        while i < len(trades):
            t = trades[i]
            trade_rows.append({
                "Time": datetime.fromtimestamp(t["ts"]).strftime("%Y-%m-%d %H:%M:%S"),
                "Ticker": str(t["symbol"]).upper(),
                "Side": str(t["side"]).upper(),
                "Qty": float(t["qty"]),
                "Price": float(t["price"])
            })
            i += 1
        trade_df = pd.DataFrame(trade_rows)
        st.dataframe(trade_df, use_container_width=True)

st.divider()

# -----------------------------
# Allocation view
# -----------------------------
section("Portfolio Allocation")

if positions_df.empty:
    st.info("Allocation view will appear after positions are opened.")
else:
    alloc_df = positions_df[["Ticker", "Weight %"]].copy()
    alloc_df = alloc_df.sort_values("Weight %", ascending=False).reset_index(drop=True)
    st.bar_chart(alloc_df.set_index("Ticker"))

st.divider()

# -----------------------------
# Workflow navigator
# -----------------------------
section("Recommended Workflow", "Suggested order for using the platform.")

w1, w2, w3, w4 = st.columns(4)
with w1:
    st.info("1. Trading Sim\n\nPlace simulated trades and build portfolio history.")
with w2:
    st.info("2. Risk Engine\n\nReview drawdown, volatility, and kill-switch status.")
with w3:
    st.info("3. Monte Carlo\n\nSimulate possible future portfolio outcomes.")
with w4:
    st.info("4. Strategy DNA / Execution\n\nUnderstand behavior and execution quality.")

st.divider()

# -----------------------------
# Quick platform notes
# -----------------------------
section("What This Dashboard Tells You")
st.write("This dashboard combines your Trading Sim, Risk Engine, bot state, and recent activity into one professional overview.")
st.write("Use it as the main landing page before going deeper into individual pages.")

if kill_switch:
    next_step("Open Risk Engine first and resolve the active risk issue before placing new trades.")
elif len(positions_df) == 0:
    next_step("Start with Trading Sim to create positions and portfolio history.")
elif len(equity) == 0:
    next_step("Use Trading Sim a bit more so the system can build portfolio analytics.")
elif len(alerts) > 0:
    next_step("Review Alerts and Risk Engine to understand what changed in the portfolio.")
else:
    next_step("You are in a good state to explore Monte Carlo, Strategy DNA, and Portfolio Optimizer.")