import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

from components.layout import setup_page, section, next_step, plotly_config

from core.bot import TradingBot
from execution.sim_broker import place_market_order, get_cash


# =============================
# Page setup
# =============================
setup_page(
    "Trading Bot",
    "Generate rule-based buy, sell, or hold signals and optionally execute them in the simulated broker.",
    "🤖"
)


# -----------------------------
# Kill Switch Check
# -----------------------------
if st.session_state.get("kill_switch", False):
    st.error("Trading Disabled Due to Risk Limits")

    reasons = st.session_state.get("kill_switch_reasons", [])

    i = 0
    while i < len(reasons):
        st.write(f"- {reasons[i]}")
        i += 1

    st.stop()


# -----------------------------
# Sidebar Settings
# -----------------------------
st.sidebar.header("Bot Settings")

symbol = st.sidebar.text_input(
    "Symbol",
    value="AAPL"
).upper().strip()

period = st.sidebar.selectbox(
    "Data Period",
    ["1mo", "3mo", "6mo"],
    index=1
)

interval = st.sidebar.selectbox(
    "Interval",
    ["1d", "1h"],
    index=0
)

short_window = st.sidebar.slider(
    "Short MA Window",
    3,
    20,
    5
)

long_window = st.sidebar.slider(
    "Long MA Window",
    10,
    50,
    20
)

risk_pct = st.sidebar.slider(
    "Risk % Per Trade",
    0.005,
    0.05,
    0.02
)

max_position_value = st.sidebar.number_input(
    "Max Position Value",
    value=20000.0
)

run_bot = st.sidebar.button(
    "Run Bot",
    use_container_width=True
)


# -----------------------------
# Waiting State
# -----------------------------
if not run_bot:
    st.info("Configure bot settings in the sidebar and click Run Bot.")
    st.stop()


# -----------------------------
# Load Data
# -----------------------------
section(
    "Market Data",
    "Download price history and prepare moving-average features."
)

data = yf.download(
    symbol,
    period=period,
    interval=interval,
    auto_adjust=True,
    progress=False
)

if data is None or data.empty:
    st.error("Could not fetch market data.")
    st.stop()

if isinstance(data.columns, pd.MultiIndex):
    close = data["Close"]

    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

else:
    close = data["Close"]

close = pd.Series(close).dropna()

if len(close) < long_window:
    st.warning("Not enough data for moving averages.")
    st.stop()

st.success(f"Loaded {len(close)} price bars for {symbol}.")

st.divider()


# -----------------------------
# Initialize Bot
# -----------------------------
bot = TradingBot(
    short_window=short_window,
    long_window=long_window,
    risk_pct=risk_pct,
    max_position_value=max_position_value
)

cash = float(get_cash())

result = bot.analyze(close, cash)

st.session_state["bot_signal"] = result["signal"]
st.session_state["bot_reason"] = result["reason"]


# -----------------------------
# Display Results
# -----------------------------
section(
    "Bot Decision",
    "Current rule-based signal and suggested trade sizing."
)

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Signal", result["signal"].upper())
c2.metric("Latest Price", f"${result['latest_price']:.2f}")
c3.metric("Suggested Qty", f"{result['suggested_qty']:.2f}")
c4.metric("Volatility", f"{result['volatility']:.4f}")
c5.metric("Available Cash", f"${cash:,.2f}")

st.write("Reason:", result["reason"])

if result["signal"] == "buy":
    st.success("Bot signal is BUY. Trend structure is positive.")
elif result["signal"] == "sell":
    st.error("Bot signal is SELL. Trend structure is negative.")
else:
    st.info("Bot signal is HOLD. No strong trend edge detected.")

st.divider()


# -----------------------------
# Price Chart
# -----------------------------
section(
    "Price + Moving Averages",
    "Visualize the moving-average crossover logic behind the bot decision."
)

df = bot.prepare_data(close)

chart_df = pd.DataFrame({
    "Price": df["price"],
    "Short MA": df["short_ma"],
    "Long MA": df["long_ma"]
})

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=chart_df.index.tolist(),
    y=chart_df["Price"].tolist(),
    mode="lines",
    name="Price",
    line=dict(color="#10b981", width=2)
))
fig.add_trace(go.Scatter(
    x=chart_df.index.tolist(),
    y=chart_df["Short MA"].tolist(),
    mode="lines",
    name="Short MA",
    line=dict(color="#3b82f6", width=1)
))
fig.add_trace(go.Scatter(
    x=chart_df.index.tolist(),
    y=chart_df["Long MA"].tolist(),
    mode="lines",
    name="Long MA",
    line=dict(color="#f59e0b", width=1)
))
fig.update_layout(title="Price + Moving Averages", xaxis_title="Date", yaxis_title="Price", **plotly_config())
st.plotly_chart(fig, use_container_width=True)

st.divider()


# -----------------------------
# Execute Trade
# -----------------------------
section(
    "Execute Bot Trade",
    "Send the bot's suggested order into the simulated broker."
)

execute = st.button(
    "Execute Bot Trade",
    type="primary"
)

if execute:
    signal = result["signal"]
    qty = result["suggested_qty"]
    price = result["latest_price"]

    if signal == "hold":
        st.warning("Bot suggests HOLD. No trade executed.")

    elif qty <= 0:
        st.warning("Suggested quantity is too small.")

    else:
        res = place_market_order(
            symbol,
            qty,
            signal,
            price
        )

        if res.get("ok"):
            st.success(f"{signal.upper()} order executed.")
            st.write(res)

        else:
            st.error(res.get("error", "Order failed"))

st.divider()


# -----------------------------
# Bot Insight
# -----------------------------
section(
    "Bot Insight",
    "Plain-English interpretation of the trading signal."
)

if result["signal"] == "buy":
    st.success("Trend is positive. Bot favors upward momentum.")

elif result["signal"] == "sell":
    st.error("Trend is negative. Bot favors downside or exit behavior.")

else:
    st.info("No strong trend detected. Bot is waiting.")

next_step(
    "Use Trading Sim, Risk Engine, or Alerts next to monitor the effect of bot-driven trades."
)
