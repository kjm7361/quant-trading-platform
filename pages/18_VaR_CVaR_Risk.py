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
    "VaR / CVaR Risk Engine",
    "Estimate downside portfolio risk using Historical VaR, CVaR, Parametric VaR, drawdowns, and tail-loss analysis.",
    "⚠️"
)


# =============================
# Helper functions
# =============================
def load_price_data(tickers, period, interval):
    try:
        data = yf.download(
            tickers,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False
        )

        if data is None or data.empty:
            return pd.DataFrame()

        if isinstance(data.columns, pd.MultiIndex):
            if "Close" in data.columns.get_level_values(0):
                close = data["Close"].copy()
            else:
                return pd.DataFrame()
        else:
            if "Close" in data.columns:
                close = pd.DataFrame(data["Close"])
                close.columns = [tickers[0]]
            else:
                return pd.DataFrame()

        close = close.dropna(how="all")
        close = close.ffill()

        return close

    except Exception:
        return pd.DataFrame()


def parse_tickers(text):
    raw = str(text).replace(" ", "").upper().split(",")

    tickers = []

    i = 0
    while i < len(raw):
        t = raw[i].strip()

        if t != "" and t not in tickers:
            tickers.append(t)

        i += 1

    return tickers


def equal_weights(n):
    if n <= 0:
        return np.array([])

    return np.ones(n) / n


def portfolio_returns(price_df, weights):
    returns = price_df.pct_change().dropna()

    if returns.empty:
        return pd.Series(dtype=float)

    w = np.array(weights, dtype=float)

    if len(w) != returns.shape[1]:
        w = equal_weights(returns.shape[1])

    port_rets = returns.dot(w)

    return pd.Series(port_rets, index=returns.index).dropna()


def compute_drawdown(equity):
    equity = pd.Series(equity).dropna()

    if len(equity) == 0:
        return pd.Series(dtype=float)

    return equity / equity.cummax() - 1


def historical_var(returns, confidence_level):
    returns = pd.Series(returns).dropna()

    if len(returns) == 0:
        return 0.0

    percentile = (1 - confidence_level) * 100

    return float(np.percentile(returns, percentile))


def historical_cvar(returns, confidence_level):
    returns = pd.Series(returns).dropna()

    if len(returns) == 0:
        return 0.0

    var_value = historical_var(returns, confidence_level)

    tail_losses = returns[returns <= var_value]

    if len(tail_losses) == 0:
        return var_value

    return float(tail_losses.mean())


def parametric_var(returns, confidence_level):
    returns = pd.Series(returns).dropna()

    if len(returns) < 2:
        return 0.0

    mean = float(returns.mean())
    std = float(returns.std())

    z_map = {
        0.90: 1.2816,
        0.95: 1.6449,
        0.99: 2.3263
    }

    z = z_map.get(round(confidence_level, 2), 1.6449)

    return mean - z * std


def safe_sharpe(returns):
    returns = pd.Series(returns).dropna()

    if len(returns) < 2:
        return 0.0

    std = float(returns.std())

    if std == 0:
        return 0.0

    return float((returns.mean() / (std + 1e-9)) * np.sqrt(252))


def safe_sortino(returns):
    returns = pd.Series(returns).dropna()

    if len(returns) < 2:
        return 0.0

    downside = returns[returns < 0]

    if len(downside) == 0:
        return 0.0

    downside_std = float(downside.std())

    if downside_std == 0:
        return 0.0

    return float((returns.mean() / (downside_std + 1e-9)) * np.sqrt(252))


def risk_label(var_value, cvar_value, max_dd):
    abs_var = abs(float(var_value))
    abs_cvar = abs(float(cvar_value))
    abs_dd = abs(float(max_dd))

    if abs_cvar > 0.05 or abs_dd > 0.25:
        return "High Risk"

    if abs_cvar > 0.03 or abs_dd > 0.15:
        return "Moderate Risk"

    return "Controlled Risk"


def risk_message(label):
    if label == "High Risk":
        return "Tail risk is elevated. Consider reducing exposure, hedging, or tightening the kill switch."

    if label == "Moderate Risk":
        return "Risk is meaningful but not extreme. Monitor drawdowns and position sizing carefully."

    return "Risk appears controlled under the selected assumptions."


# =============================
# Sidebar
# =============================
st.sidebar.header("VaR Settings")

data_mode = st.sidebar.selectbox(
    "Data Source",
    ["Use Session Portfolio", "Use Custom Tickers"],
    index=0
)

ticker_text = st.sidebar.text_input(
    "Tickers",
    value="AAPL,MSFT,NVDA,SPY,QQQ"
)

period = st.sidebar.selectbox(
    "Lookback Period",
    ["6mo", "1y", "2y", "5y"],
    index=1
)

interval = st.sidebar.selectbox(
    "Interval",
    ["1d", "1wk"],
    index=0
)

confidence_level = st.sidebar.selectbox(
    "Confidence Level",
    [0.90, 0.95, 0.99],
    index=1
)

starting_capital = st.sidebar.number_input(
    "Portfolio Value ($)",
    min_value=1000.0,
    value=100000.0,
    step=1000.0
)

run = st.sidebar.button(
    "Run VaR Analysis",
    use_container_width=True
)


# =============================
# Waiting state
# =============================
if not run:
    st.info("Choose VaR settings in the sidebar and click Run VaR Analysis.")
    st.stop()


# =============================
# Load returns
# =============================
section(
    "Risk Data",
    "Load return series from either the active session portfolio or a custom basket of tickers."
)

returns = pd.Series(dtype=float)
source_label = ""

if data_mode == "Use Session Portfolio":
    session_returns = st.session_state.get("strategy_returns", None)

    if session_returns is not None and len(session_returns) > 0:
        returns = pd.Series(session_returns).dropna()
        source_label = "Session Portfolio"

    else:
        st.warning("No session portfolio returns found. Falling back to custom tickers.")
        data_mode = "Use Custom Tickers"

if data_mode == "Use Custom Tickers":
    tickers = parse_tickers(ticker_text)

    if len(tickers) < 2:
        st.error("Enter at least two tickers.")
        st.stop()

    prices = load_price_data(
        tickers,
        period=period,
        interval=interval
    )

    if prices.empty:
        st.error("Could not load price data.")
        st.stop()

    valid_cols = []
    cols = list(prices.columns)

    i = 0
    while i < len(cols):
        c = cols[i]
        if prices[c].dropna().shape[0] > 5:
            valid_cols.append(c)
        i += 1

    prices = prices[valid_cols]

    if prices.shape[1] < 2:
        st.error("Not enough valid ticker data.")
        st.stop()

    weights = equal_weights(prices.shape[1])

    returns = portfolio_returns(prices, weights)
    source_label = "Custom Equal-Weight Basket"

if len(returns) < 5:
    st.warning("Not enough return observations for reliable VaR analysis.")
    st.stop()

returns = returns.dropna()

equity = (1 + returns).cumprod()
drawdown = compute_drawdown(equity)

st.success(f"Using {source_label} with {len(returns)} return observations.")

st.divider()


# =============================
# Compute metrics
# =============================
hist_var = historical_var(returns, confidence_level)
hist_cvar = historical_cvar(returns, confidence_level)
para_var = parametric_var(returns, confidence_level)

max_dd = float(drawdown.min())
volatility = float(returns.std() * np.sqrt(252))
sharpe = safe_sharpe(returns)
sortino = safe_sortino(returns)
mean_return = float(returns.mean() * 252)

var_dollars = abs(hist_var) * starting_capital
cvar_dollars = abs(hist_cvar) * starting_capital
para_var_dollars = abs(para_var) * starting_capital

label = risk_label(hist_var, hist_cvar, max_dd)


# =============================
# Summary
# =============================
section(
    "VaR / CVaR Summary",
    "Estimated loss thresholds for the selected confidence level."
)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Historical VaR",
    f"{hist_var*100:.2f}%",
    f"-${var_dollars:,.2f}"
)

c2.metric(
    "Historical CVaR",
    f"{hist_cvar*100:.2f}%",
    f"-${cvar_dollars:,.2f}"
)

c3.metric(
    "Parametric VaR",
    f"{para_var*100:.2f}%",
    f"-${para_var_dollars:,.2f}"
)

c4.metric(
    "Risk Label",
    label
)

st.info(risk_message(label))

st.divider()


# =============================
# Portfolio risk metrics
# =============================
section(
    "Portfolio Risk Metrics",
    "Annualized return, volatility, Sharpe, Sortino, and drawdown."
)

m1, m2, m3, m4, m5 = st.columns(5)

m1.metric("Annual Return", f"{mean_return*100:.2f}%")
m2.metric("Annual Volatility", f"{volatility*100:.2f}%")
m3.metric("Sharpe Ratio", f"{sharpe:.2f}")
m4.metric("Sortino Ratio", f"{sortino:.2f}")
m5.metric("Max Drawdown", f"{max_dd*100:.2f}%")

st.divider()


# =============================
# Tail-loss chart
# =============================
section(
    "Return Distribution and Tail Losses",
    "Visualize the return distribution and downside loss threshold."
)

fig1, ax1 = plt.subplots(figsize=(11, 5))

ax1.hist(
    returns,
    bins=50,
    alpha=0.75
)

ax1.axvline(
    hist_var,
    linestyle="--",
    linewidth=2,
    label=f"Historical VaR {confidence_level:.0%}"
)

ax1.axvline(
    hist_cvar,
    linestyle="--",
    linewidth=2,
    label=f"Historical CVaR {confidence_level:.0%}"
)

ax1.set_title("Portfolio Return Distribution")
ax1.set_xlabel("Return")
ax1.set_ylabel("Frequency")
ax1.legend()

st.pyplot(fig1)

st.divider()


# =============================
# Equity and drawdown
# =============================
section(
    "Equity and Drawdown",
    "Portfolio growth and maximum loss from prior peaks."
)

c1, c2 = st.columns(2)

with c1:
    st.subheader("Equity Curve")
    st.line_chart(equity)

with c2:
    st.subheader("Drawdown Curve")
    st.line_chart(drawdown)

st.divider()


# =============================
# Tail observations
# =============================
section(
    "Worst Return Observations",
    "Worst individual return periods in the selected sample."
)

worst_returns = (
    returns
    .sort_values()
    .head(15)
    .reset_index()
)

worst_returns.columns = ["Date", "Return"]

st.dataframe(
    worst_returns.style.format({
        "Return": "{:.2%}"
    }),
    use_container_width=True
)

st.divider()


# =============================
# Stress test
# =============================
section(
    "Stress Loss Estimates",
    "Estimated dollar loss under different downside assumptions."
)

stress_df = pd.DataFrame({
    "Scenario": [
        "1-Day Historical VaR",
        "1-Day Historical CVaR",
        "1-Day Parametric VaR",
        "Maximum Historical Drawdown"
    ],
    "Return Shock": [
        hist_var,
        hist_cvar,
        para_var,
        max_dd
    ],
    "Estimated Dollar Loss": [
        -abs(hist_var) * starting_capital,
        -abs(hist_cvar) * starting_capital,
        -abs(para_var) * starting_capital,
        -abs(max_dd) * starting_capital
    ]
})

st.dataframe(
    stress_df.style.format({
        "Return Shock": "{:.2%}",
        "Estimated Dollar Loss": "${:,.2f}"
    }),
    use_container_width=True
)


# =============================
# Save state
# =============================
st.session_state["portfolio_var"] = float(hist_var)
st.session_state["portfolio_cvar"] = float(hist_cvar)
st.session_state["portfolio_parametric_var"] = float(para_var)
st.session_state["portfolio_risk_label"] = label


# =============================
# Next step
# =============================
next_step(
    "Use Risk Engine, Alerts, or Monte Carlo next to compare VaR estimates against active risk limits."
)