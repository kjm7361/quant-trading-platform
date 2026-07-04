import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

from statsmodels.tsa.stattools import coint
from components.layout import setup_page, section, next_step, plotly_config


# =============================
# Page setup
# =============================
setup_page(
    "Pairs Trading + Cointegration",
    "Build a statistical arbitrage strategy using correlation, cointegration, spread z-scores, and mean reversion signals.",
    "🔁"
)


# =============================
# Helper functions
# =============================
def load_pair_data(ticker1, ticker2, period):
    data = yf.download(
        [ticker1, ticker2],
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False
    )

    if data is None or data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"].copy()
    else:
        close = data[["Close"]].copy()
        close.columns = [ticker1]

    close = close.dropna()

    return close


def compute_spread(y, x):
    x_values = np.array(x)
    y_values = np.array(y)

    beta = np.polyfit(x_values, y_values, 1)[0]

    spread = y_values - beta * x_values

    return pd.Series(spread, index=y.index), beta


def compute_zscore(spread, window):
    mean = spread.rolling(window).mean()
    std = spread.rolling(window).std()

    z = (spread - mean) / std

    return z


def generate_signals(zscore, entry_z, exit_z):
    signal = pd.Series(0, index=zscore.index)

    i = 0
    while i < len(zscore):
        z = zscore.iloc[i]

        if z > entry_z:
            signal.iloc[i] = -1

        elif z < -entry_z:
            signal.iloc[i] = 1

        elif abs(z) < exit_z:
            signal.iloc[i] = 0

        else:
            if i > 0:
                signal.iloc[i] = signal.iloc[i - 1]

        i += 1

    return signal


def backtest_pair_strategy(price1, price2, signal):
    r1 = price1.pct_change()
    r2 = price2.pct_change()

    shifted_signal = signal.shift(1).fillna(0)

    strategy_returns = shifted_signal * (r1 - r2)

    strategy_returns = strategy_returns.dropna()

    equity = (1 + strategy_returns).cumprod()

    if len(equity) > 0:
        equity = equity / equity.iloc[0]

    return strategy_returns, equity


def max_drawdown(equity):
    if len(equity) == 0:
        return 0.0

    dd = equity / equity.cummax() - 1

    return float(dd.min())


def sharpe_ratio(returns):
    if len(returns) < 2:
        return 0.0

    std = float(returns.std())

    if std == 0:
        return 0.0

    return float((returns.mean() / std) * np.sqrt(252))


def trade_count(signal):
    changes = signal.diff().abs()

    return int((changes > 0).sum())


# =============================
# Sidebar
# =============================
st.sidebar.header("Pairs Trading Settings")

ticker1 = st.sidebar.text_input("Ticker 1", value="KO").upper().strip()
ticker2 = st.sidebar.text_input("Ticker 2", value="PEP").upper().strip()

period = st.sidebar.selectbox(
    "Lookback Period",
    ["6mo", "1y", "2y", "5y"],
    index=2
)

z_window = st.sidebar.slider(
    "Z-Score Window",
    10,
    120,
    30,
    5
)

entry_z = st.sidebar.slider(
    "Entry Z-Score",
    1.0,
    3.0,
    2.0,
    0.1
)

exit_z = st.sidebar.slider(
    "Exit Z-Score",
    0.1,
    1.5,
    0.5,
    0.1
)

run = st.sidebar.button(
    "Run Pairs Trading Analysis",
    use_container_width=True
)


if not run:
    st.info("Enter two related tickers and click Run Pairs Trading Analysis.")
    st.stop()


# =============================
# Load data
# =============================
section(
    "Pair Data",
    "Download historical prices and prepare the two-asset pair."
)

prices = load_pair_data(ticker1, ticker2, period)

if prices.empty:
    st.error("Could not load pair data.")
    st.stop()

if ticker1 not in prices.columns or ticker2 not in prices.columns:
    st.error("One or both tickers could not be loaded.")
    st.stop()

price1 = prices[ticker1].dropna()
price2 = prices[ticker2].dropna()

combined = pd.concat([price1, price2], axis=1).dropna()
combined.columns = [ticker1, ticker2]

if len(combined) < z_window + 10:
    st.warning("Not enough data for selected z-score window.")
    st.stop()

st.success(f"Loaded {len(combined)} observations for {ticker1} and {ticker2}.")

st.divider()


# =============================
# Correlation + cointegration
# =============================
section(
    "Correlation and Cointegration",
    "Check whether the pair has statistical relationship useful for mean-reversion trading."
)

corr = float(combined[ticker1].pct_change().corr(combined[ticker2].pct_change()))

score, pvalue, _ = coint(combined[ticker1], combined[ticker2])

c1, c2, c3 = st.columns(3)

c1.metric("Return Correlation", f"{corr:.3f}")
c2.metric("Cointegration p-value", f"{pvalue:.4f}")

if pvalue < 0.05:
    c3.metric("Cointegration Result", "Likely Cointegrated")
    st.success("The pair appears cointegrated at the 5% level. This is favorable for pairs trading.")
else:
    c3.metric("Cointegration Result", "Not Strong")
    st.warning("The pair does not show strong cointegration. Strategy may be less reliable.")

st.divider()


# =============================
# Spread + z-score
# =============================
section(
    "Spread and Z-Score",
    "Construct hedge-ratio adjusted spread and identify deviations from normal relationship."
)

spread, beta = compute_spread(combined[ticker1], combined[ticker2])
zscore = compute_zscore(spread, z_window)

signal = generate_signals(
    zscore,
    entry_z=entry_z,
    exit_z=exit_z
)

latest_z = float(zscore.dropna().iloc[-1])

s1, s2, s3 = st.columns(3)

s1.metric("Hedge Ratio Beta", f"{beta:.4f}")
s2.metric("Latest Z-Score", f"{latest_z:.2f}")

if latest_z > entry_z:
    s3.metric("Current Signal", f"Short {ticker1} / Long {ticker2}")
elif latest_z < -entry_z:
    s3.metric("Current Signal", f"Long {ticker1} / Short {ticker2}")
else:
    s3.metric("Current Signal", "No Entry / Hold")

st.divider()


# =============================
# Price chart
# =============================
section(
    "Pair Price Chart",
    "Normalized price movement of both assets."
)

normalized = combined / combined.iloc[0]

fig_norm = go.Figure()
fig_norm.add_trace(go.Scatter(
    x=normalized.index.tolist(),
    y=normalized[ticker1].tolist(),
    mode="lines",
    name=ticker1,
    line=dict(color="#10b981", width=2)
))
fig_norm.add_trace(go.Scatter(
    x=normalized.index.tolist(),
    y=normalized[ticker2].tolist(),
    mode="lines",
    name=ticker2,
    line=dict(color="#3b82f6", width=2)
))
fig_norm.update_layout(title="Normalized Pair Prices", xaxis_title="Date", yaxis_title="Normalized Price", **plotly_config())
st.plotly_chart(fig_norm, use_container_width=True)

st.divider()


# =============================
# Spread chart
# =============================
section(
    "Spread Chart",
    "Mean-reversion spread between the two assets."
)

fig_spread = go.Figure(go.Scatter(
    x=spread.index.tolist(),
    y=spread.values.tolist(),
    mode="lines",
    name="Spread",
    line=dict(color="#10b981", width=2)
))
fig_spread.add_hline(y=float(spread.mean()), line_dash="dash", line_color="#94a3b8", annotation_text="Mean")
fig_spread.update_layout(title="Hedge-Ratio Adjusted Spread", xaxis_title="Date", yaxis_title="Spread", **plotly_config())
st.plotly_chart(fig_spread, use_container_width=True)

st.divider()


# =============================
# Z-score chart
# =============================
section(
    "Z-Score Signal Chart",
    "Entry and exit signals based on spread deviation."
)

fig_z = go.Figure(go.Scatter(
    x=zscore.index.tolist(),
    y=zscore.values.tolist(),
    mode="lines",
    name="Z-Score",
    line=dict(color="#10b981", width=2)
))
fig_z.add_hline(y=entry_z, line_dash="dash", line_color="#ef4444", annotation_text="Short Spread Entry")
fig_z.add_hline(y=-entry_z, line_dash="dash", line_color="#3b82f6", annotation_text="Long Spread Entry")
fig_z.add_hline(y=exit_z, line_dash="dot", line_color="#94a3b8", annotation_text="Exit")
fig_z.add_hline(y=-exit_z, line_dash="dot", line_color="#94a3b8")
fig_z.add_hline(y=0, line_color="#94a3b8", line_width=1)
fig_z.update_layout(title="Spread Z-Score", xaxis_title="Date", yaxis_title="Z-Score", **plotly_config())
st.plotly_chart(fig_z, use_container_width=True)

st.divider()


# =============================
# Backtest
# =============================
section(
    "Pairs Trading Backtest",
    "Simulate a simple long-short mean-reversion strategy."
)

returns, equity = backtest_pair_strategy(
    combined[ticker1],
    combined[ticker2],
    signal
)

if len(equity) == 0:
    st.warning("Not enough strategy returns to backtest.")
    st.stop()

total_return = float(equity.iloc[-1] - 1)
sharpe = sharpe_ratio(returns)
mdd = max_drawdown(equity)
trades = trade_count(signal)

b1, b2, b3, b4 = st.columns(4)

b1.metric("Total Return", f"{total_return*100:.2f}%")
b2.metric("Sharpe Ratio", f"{sharpe:.2f}")
b3.metric("Max Drawdown", f"{mdd*100:.2f}%")
b4.metric("Signal Changes", str(trades))

st.subheader("Strategy Equity Curve")

fig_eq = go.Figure(go.Scatter(
    x=equity.index.tolist(),
    y=equity.values.tolist(),
    mode="lines",
    name="Equity",
    line=dict(color="#10b981", width=2)
))
fig_eq.update_layout(title="Strategy Equity Curve", xaxis_title="Date", yaxis_title="Equity", **plotly_config())
st.plotly_chart(fig_eq, use_container_width=True)

st.divider()


# =============================
# Signal table
# =============================
section(
    "Signal Table",
    "Latest pair spread, z-score, and position signal."
)

signal_table = pd.DataFrame({
    ticker1: combined[ticker1],
    ticker2: combined[ticker2],
    "Spread": spread,
    "Z-Score": zscore,
    "Signal": signal
}).dropna()

signal_table["Interpretation"] = "No Position"

signal_table.loc[signal_table["Signal"] == 1, "Interpretation"] = f"Long {ticker1} / Short {ticker2}"
signal_table.loc[signal_table["Signal"] == -1, "Interpretation"] = f"Short {ticker1} / Long {ticker2}"

st.dataframe(
    signal_table.tail(50).style.format({
        ticker1: "{:.2f}",
        ticker2: "{:.2f}",
        "Spread": "{:.4f}",
        "Z-Score": "{:.2f}"
    }),
    use_container_width=True
)

st.divider()


# =============================
# Interpretation
# =============================
section(
    "Plain-English Interpretation",
    "How to understand the pair trading result."
)

if pvalue < 0.05 and abs(latest_z) > entry_z:
    st.success("This pair currently shows both cointegration and a strong spread deviation. It may be a reasonable statistical arbitrage candidate.")

elif pvalue < 0.05:
    st.info("This pair appears cointegrated, but the current spread is not far enough from normal to trigger a strong entry.")

elif abs(latest_z) > entry_z:
    st.warning("The spread is far from normal, but the pair is not strongly cointegrated. Be careful with mean-reversion assumptions.")

else:
    st.warning("This pair does not currently show a strong statistical arbitrage setup.")

st.write(
    "A good pairs trade usually needs both a stable long-term relationship and a temporary short-term dislocation."
)


# =============================
# Save state
# =============================
st.session_state["pairs_ticker1"] = ticker1
st.session_state["pairs_ticker2"] = ticker2
st.session_state["pairs_correlation"] = corr
st.session_state["pairs_cointegration_pvalue"] = float(pvalue)
st.session_state["pairs_latest_zscore"] = latest_z
st.session_state["pairs_total_return"] = total_return
st.session_state["pairs_sharpe"] = sharpe


# =============================
# Next step
# =============================
next_step(
    "Use Market Regime Detection or Risk Engine next to check whether current market conditions support mean-reversion trading."
)
