import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

from components.layout import setup_page, section, next_step


# =============================
# Page setup
# =============================
setup_page(
    "Market Regime Detection",
    "Classify market conditions into bull, bear, sideways, high-volatility, and stress regimes.",
    "🌎"
)


# =============================
# Helper functions
# =============================
def load_market_data(symbol, period, interval):
    try:
        data = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False
        )

        if data is None or data.empty:
            return pd.DataFrame()

        if isinstance(data.columns, pd.MultiIndex):
            if "Close" in data.columns.get_level_values(0):
                close = data["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
            else:
                return pd.DataFrame()
        else:
            if "Close" in data.columns:
                close = data["Close"]
            else:
                return pd.DataFrame()

        df = pd.DataFrame()
        df["Close"] = pd.Series(close).dropna()
        df["Return"] = df["Close"].pct_change()
        df = df.dropna()

        return df

    except Exception:
        return pd.DataFrame()


def compute_regime_features(df, short_window, long_window, vol_window):
    out = df.copy()

    out["SMA_Short"] = out["Close"].rolling(short_window).mean()
    out["SMA_Long"] = out["Close"].rolling(long_window).mean()

    out["Trend_Return"] = out["Close"].pct_change(long_window)
    out["Rolling_Vol"] = out["Return"].rolling(vol_window).std() * np.sqrt(252)

    out["Drawdown"] = out["Close"] / out["Close"].cummax() - 1

    out = out.dropna()

    return out


def classify_regime(row, vol_threshold, stress_dd):
    close = float(row["Close"])
    sma_short = float(row["SMA_Short"])
    sma_long = float(row["SMA_Long"])
    rolling_vol = float(row["Rolling_Vol"])
    drawdown = float(row["Drawdown"])

    if drawdown <= stress_dd and rolling_vol >= vol_threshold:
        return "Stress"

    if sma_short > sma_long and close > sma_long:
        if rolling_vol >= vol_threshold:
            return "High-Vol Bull"
        return "Bull"

    if sma_short < sma_long and close < sma_long:
        if rolling_vol >= vol_threshold:
            return "High-Vol Bear"
        return "Bear"

    if rolling_vol >= vol_threshold:
        return "High-Vol Sideways"

    return "Sideways"


def regime_color(regime):
    if regime == "Bull":
        return "🟢"
    if regime == "High-Vol Bull":
        return "🟡"
    if regime == "Bear":
        return "🔴"
    if regime == "High-Vol Bear":
        return "🟠"
    if regime == "Stress":
        return "🚨"
    if regime == "High-Vol Sideways":
        return "🟣"
    return "⚪"


def regime_explanation(regime):
    if regime == "Bull":
        return "Market is trending upward with controlled volatility."
    if regime == "High-Vol Bull":
        return "Market trend is positive, but volatility is elevated."
    if regime == "Bear":
        return "Market is trending downward with controlled volatility."
    if regime == "High-Vol Bear":
        return "Market trend is negative and volatility is elevated."
    if regime == "Stress":
        return "Market is in a drawdown with elevated volatility. Risk should be reduced."
    if regime == "High-Vol Sideways":
        return "Market direction is unclear, but volatility is elevated."
    return "Market has no strong trend and volatility is normal."


# =============================
# Sidebar controls
# =============================
st.sidebar.header("Regime Settings")

symbol = st.sidebar.selectbox(
    "Market Proxy",
    ["SPY", "QQQ", "IWM", "DIA"],
    index=0
)

period = st.sidebar.selectbox(
    "Lookback Period",
    ["6mo", "1y", "2y", "5y"],
    index=2
)

interval = st.sidebar.selectbox(
    "Interval",
    ["1d", "1wk"],
    index=0
)

short_window = st.sidebar.slider(
    "Short Moving Average",
    10,
    100,
    50,
    5
)

long_window = st.sidebar.slider(
    "Long Moving Average",
    50,
    250,
    200,
    10
)

vol_window = st.sidebar.slider(
    "Volatility Window",
    10,
    90,
    30,
    5
)

vol_threshold = st.sidebar.slider(
    "High Volatility Threshold",
    0.10,
    0.60,
    0.25,
    0.01
)

stress_dd = st.sidebar.slider(
    "Stress Drawdown Threshold",
    -0.50,
    -0.05,
    -0.15,
    0.01
)

run = st.sidebar.button(
    "Detect Regime",
    use_container_width=True
)


# =============================
# Waiting state
# =============================
if not run:
    st.info("Choose market regime settings in the sidebar and click Detect Regime.")
    st.stop()


# =============================
# Load data
# =============================
section(
    "Market Data",
    "Download benchmark price history and compute trend, volatility, and drawdown features."
)

df = load_market_data(symbol, period, interval)

if df.empty:
    st.error("Could not load market data.")
    st.stop()

features = compute_regime_features(
    df,
    short_window=short_window,
    long_window=long_window,
    vol_window=vol_window
)

if features.empty:
    st.warning("Not enough data to compute regime features. Try a longer lookback period.")
    st.stop()

features["Regime"] = features.apply(
    lambda row: classify_regime(
        row,
        vol_threshold=vol_threshold,
        stress_dd=stress_dd
    ),
    axis=1
)

latest = features.iloc[-1]
current_regime = latest["Regime"]

st.success(f"Loaded {len(features)} usable observations for {symbol}.")

st.divider()


# =============================
# Regime summary
# =============================
section(
    "Current Market Regime",
    "Latest detected market environment based on trend, volatility, and drawdown."
)

r1, r2, r3, r4 = st.columns(4)

r1.metric("Current Regime", f"{regime_color(current_regime)} {current_regime}")
r2.metric("Latest Close", f"${float(latest['Close']):,.2f}")
r3.metric("Annualized Volatility", f"{float(latest['Rolling_Vol'])*100:.2f}%")
r4.metric("Current Drawdown", f"{float(latest['Drawdown'])*100:.2f}%")

st.info(regime_explanation(current_regime))

st.divider()


# =============================
# Risk recommendation
# =============================
section(
    "Regime-Based Risk Recommendation",
    "Simple portfolio behavior suggestion based on the current detected regime."
)

if current_regime == "Bull":
    st.success("Risk posture: Normal to moderately aggressive. Trend-following strategies may perform better.")

elif current_regime == "High-Vol Bull":
    st.warning("Risk posture: Selective. Trend is positive, but position sizes should be controlled.")

elif current_regime == "Bear":
    st.warning("Risk posture: Defensive. Reduce long exposure and monitor downside risk.")

elif current_regime == "High-Vol Bear":
    st.error("Risk posture: Defensive. Avoid overexposure and prioritize capital preservation.")

elif current_regime == "Stress":
    st.error("Risk posture: Risk-off. Consider reducing exposure, tightening limits, or pausing new trades.")

elif current_regime == "High-Vol Sideways":
    st.warning("Risk posture: Neutral/defensive. Mean-reversion may work, but volatility risk is elevated.")

else:
    st.info("Risk posture: Neutral. Wait for stronger trend confirmation.")

st.divider()


# =============================
# Regime distribution
# =============================
section(
    "Regime Distribution",
    "How often each regime occurred over the selected lookback period."
)

regime_counts = (
    features["Regime"]
    .value_counts()
    .reset_index()
)

regime_counts.columns = ["Regime", "Count"]
regime_counts["Share"] = regime_counts["Count"] / regime_counts["Count"].sum()

d1, d2 = st.columns([1, 2])

with d1:
    st.dataframe(
        regime_counts.style.format({
            "Share": "{:.2%}"
        }),
        use_container_width=True
    )

with d2:
    fig_counts, ax_counts = plt.subplots(figsize=(10, 4))
    ax_counts.bar(regime_counts["Regime"], regime_counts["Count"])
    ax_counts.set_title("Regime Frequency")
    ax_counts.set_xlabel("Regime")
    ax_counts.set_ylabel("Observations")
    plt.xticks(rotation=25)
    st.pyplot(fig_counts)

st.divider()


# =============================
# Price and moving averages
# =============================
section(
    "Price Trend Analysis",
    "Price relative to short and long moving averages."
)

price_chart = features[["Close", "SMA_Short", "SMA_Long"]].copy()

st.line_chart(price_chart)

st.divider()


# =============================
# Volatility and drawdown
# =============================
section(
    "Volatility and Drawdown",
    "Risk conditions used to detect high-volatility and stress regimes."
)

c1, c2 = st.columns(2)

with c1:
    st.subheader("Rolling Volatility")
    st.line_chart(features["Rolling_Vol"])

with c2:
    st.subheader("Drawdown")
    st.line_chart(features["Drawdown"])

st.divider()


# =============================
# Regime timeline
# =============================
section(
    "Regime Timeline",
    "Historical list of detected regimes over time."
)

timeline = features[[
    "Close",
    "SMA_Short",
    "SMA_Long",
    "Rolling_Vol",
    "Drawdown",
    "Regime"
]].copy()

timeline = timeline.tail(250)

st.dataframe(
    timeline.style.format({
        "Close": "{:.2f}",
        "SMA_Short": "{:.2f}",
        "SMA_Long": "{:.2f}",
        "Rolling_Vol": "{:.2%}",
        "Drawdown": "{:.2%}"
    }),
    use_container_width=True
)

st.divider()


# =============================
# Regime return analysis
# =============================
section(
    "Regime Return Analysis",
    "Average market return and volatility under each detected regime."
)

regime_stats = (
    features
    .groupby("Regime")
    .agg(
        Avg_Return=("Return", "mean"),
        Volatility=("Return", "std"),
        Observations=("Return", "count")
    )
    .reset_index()
)

regime_stats["Annualized_Return"] = regime_stats["Avg_Return"] * 252
regime_stats["Annualized_Volatility"] = regime_stats["Volatility"] * np.sqrt(252)

st.dataframe(
    regime_stats.style.format({
        "Avg_Return": "{:.4%}",
        "Volatility": "{:.4%}",
        "Annualized_Return": "{:.2%}",
        "Annualized_Volatility": "{:.2%}"
    }),
    use_container_width=True
)


# =============================
# Save state for other pages
# =============================
st.session_state["current_market_regime"] = current_regime
st.session_state["market_regime_symbol"] = symbol
st.session_state["market_regime_volatility"] = float(latest["Rolling_Vol"])
st.session_state["market_regime_drawdown"] = float(latest["Drawdown"])


# =============================
# Next step
# =============================
next_step(
    "Use Risk Engine, Monte Carlo, or Portfolio Optimizer next to adjust risk based on the current market regime."
)