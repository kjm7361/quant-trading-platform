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
    "Portfolio Optimizer",
    "Build and compare optimized portfolios using historical return, volatility, covariance, and Sharpe analysis.",
    "📈"
)


# =============================
# Helpers
# =============================
def parse_tickers(text):
    raw = str(text).upper().replace(" ", "").split(",")

    tickers = []

    i = 0
    while i < len(raw):
        t = raw[i].strip()

        if t != "" and t not in tickers:
            tickers.append(t)

        i += 1

    return tickers


def load_close_prices(tickers, period="1y", interval="1d"):
    if len(tickers) == 0:
        return pd.DataFrame()

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
                close_df = data["Close"].copy()
            else:
                return pd.DataFrame()

        else:
            if "Close" in data.columns:
                close_df = pd.DataFrame(index=data.index)
                close_df[tickers[0]] = pd.to_numeric(
                    data["Close"],
                    errors="coerce"
                )
            else:
                return pd.DataFrame()

        close_df = close_df.sort_index()
        close_df = close_df.ffill().dropna(how="all")

        return close_df

    except:
        return pd.DataFrame()


def compute_returns(price_df):
    if price_df.empty:
        return pd.DataFrame()

    rets = price_df.pct_change().dropna(how="all")

    return rets


def annualized_metrics(
    weights,
    mean_returns,
    cov_matrix,
    trading_days=252
):
    w = np.array(weights, dtype=float)

    port_return = float(
        np.dot(w, mean_returns)
        * trading_days
    )

    port_vol = float(
        np.sqrt(
            np.dot(
                w.T,
                np.dot(cov_matrix * trading_days, w)
            )
        )
    )

    sharpe = 0.0

    if port_vol > 0:
        sharpe = port_return / port_vol

    return port_return, port_vol, sharpe


def normalize_weights(weights):
    w = np.array(weights, dtype=float)

    total = float(w.sum())

    if total == 0:
        return w

    return w / total


def equal_weight_portfolio(n):
    if n <= 0:
        return np.array([])

    return np.ones(n) / n


def min_variance_portfolio(cov_matrix, n_trials=5000):
    n = cov_matrix.shape[0]

    best_w = equal_weight_portfolio(n)
    best_vol = 10**9

    i = 0
    while i < n_trials:
        w = np.random.random(n)
        w = normalize_weights(w)

        vol = float(
            np.sqrt(
                np.dot(
                    w.T,
                    np.dot(cov_matrix * 252, w)
                )
            )
        )

        if vol < best_vol:
            best_vol = vol
            best_w = w

        i += 1

    return best_w


def max_sharpe_portfolio(
    mean_returns,
    cov_matrix,
    risk_free_rate=0.0,
    n_trials=5000
):
    n = len(mean_returns)

    best_w = equal_weight_portfolio(n)
    best_score = -10**9

    i = 0
    while i < n_trials:
        w = np.random.random(n)
        w = normalize_weights(w)

        port_return = float(
            np.dot(w, mean_returns)
            * 252
        )

        port_vol = float(
            np.sqrt(
                np.dot(
                    w.T,
                    np.dot(cov_matrix * 252, w)
                )
            )
        )

        if port_vol > 0:
            sharpe = (port_return - risk_free_rate) / port_vol
        else:
            sharpe = -10**9

        if sharpe > best_score:
            best_score = sharpe
            best_w = w

        i += 1

    return best_w


def risk_parity_portfolio(cov_matrix):
    n = cov_matrix.shape[0]

    variances = np.diag(cov_matrix)

    inv_vol = []

    i = 0
    while i < n:
        v = float(variances[i])

        if v <= 0:
            inv_vol.append(0.0)
        else:
            inv_vol.append(1.0 / np.sqrt(v))

        i += 1

    w = np.array(inv_vol, dtype=float)

    if w.sum() == 0:
        return equal_weight_portfolio(n)

    return normalize_weights(w)


def build_weight_df(tickers, weights):
    rows = []

    i = 0
    while i < len(tickers):
        rows.append({
            "Ticker": tickers[i],
            "Weight": float(weights[i]),
            "Weight %": float(weights[i]) * 100
        })

        i += 1

    df = pd.DataFrame(rows)

    df = (
        df
        .sort_values("Weight", ascending=False)
        .reset_index(drop=True)
    )

    return df


def create_weight_bar_chart(weight_df, title):
    fig, ax = plt.subplots(figsize=(10, 4))

    ax.bar(
        weight_df["Ticker"],
        weight_df["Weight %"]
    )

    ax.set_title(title)
    ax.set_ylabel("Weight %")
    ax.set_xlabel("Ticker")

    return fig


def simulate_efficient_cloud(
    mean_returns,
    cov_matrix,
    n_points=1500
):
    points = []
    n = len(mean_returns)

    i = 0
    while i < n_points:
        w = np.random.random(n)
        w = normalize_weights(w)

        port_return, port_vol, sharpe = annualized_metrics(
            w,
            mean_returns,
            cov_matrix
        )

        points.append({
            "Return": port_return,
            "Volatility": port_vol,
            "Sharpe": sharpe
        })

        i += 1

    return pd.DataFrame(points)


# =============================
# Sidebar settings
# =============================
st.sidebar.header("Optimizer Settings")

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
    "Data Interval",
    ["1d", "1wk"],
    index=0
)

method = st.sidebar.selectbox(
    "Optimization Method",
    [
        "Max Sharpe",
        "Minimum Volatility",
        "Equal Weight",
        "Risk Parity"
    ],
    index=0
)

risk_free_rate = st.sidebar.slider(
    "Risk-Free Rate",
    0.0,
    0.10,
    0.02,
    0.005
)

n_trials = st.sidebar.slider(
    "Search Trials",
    1000,
    15000,
    5000,
    500
)

run = st.sidebar.button(
    "Run Optimizer",
    use_container_width=True
)


# =============================
# Waiting state
# =============================
if not run:
    st.info("Choose optimizer settings in the sidebar and click Run Optimizer.")
    st.stop()


# =============================
# Load data
# =============================
section(
    "Data Loading",
    "Download historical close prices and prepare return data for optimization."
)

tickers = parse_tickers(ticker_text)

if len(tickers) < 2:
    st.warning("Enter at least 2 tickers.")
    st.stop()

price_df = load_close_prices(
    tickers,
    period=period,
    interval=interval
)

if price_df.empty:
    st.error("Could not load historical prices.")
    st.stop()

valid_cols = []
cols = list(price_df.columns)

i = 0
while i < len(cols):
    c = cols[i]

    if price_df[c].dropna().shape[0] > 2:
        valid_cols.append(c)

    i += 1

price_df = price_df[valid_cols]

if price_df.shape[1] < 2:
    st.error("Not enough valid ticker data after cleaning.")
    st.stop()

tickers = list(price_df.columns)

returns_df = compute_returns(price_df)

if returns_df.empty or returns_df.shape[0] < 5:
    st.error("Not enough return history to optimize.")
    st.stop()

st.success(f"Loaded {len(tickers)} valid assets with {len(returns_df)} return observations.")

st.divider()


# =============================
# Optimization
# =============================
section(
    "Optimization Engine",
    "Compute optimized weights based on the selected portfolio construction method."
)

mean_returns = returns_df.mean().values
cov_matrix = returns_df.cov().values

if method == "Max Sharpe":
    opt_weights = max_sharpe_portfolio(
        mean_returns,
        cov_matrix,
        risk_free_rate=risk_free_rate,
        n_trials=n_trials
    )

elif method == "Minimum Volatility":
    opt_weights = min_variance_portfolio(
        cov_matrix,
        n_trials=n_trials
    )

elif method == "Risk Parity":
    opt_weights = risk_parity_portfolio(cov_matrix)

else:
    opt_weights = equal_weight_portfolio(len(tickers))

eq_weights = equal_weight_portfolio(len(tickers))

opt_return, opt_vol, opt_sharpe = annualized_metrics(
    opt_weights,
    mean_returns,
    cov_matrix
)

eq_return, eq_vol, eq_sharpe = annualized_metrics(
    eq_weights,
    mean_returns,
    cov_matrix
)

opt_weight_df = build_weight_df(
    tickers,
    opt_weights
)

eq_weight_df = build_weight_df(
    tickers,
    eq_weights
)

st.success(f"Optimization completed using {method}.")

st.divider()


# =============================
# Portfolio summary
# =============================
section(
    "Portfolio Summary",
    "Compare optimized portfolio metrics against equal-weight allocation."
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Method", method)
c2.metric("Expected Return", f"{opt_return*100:.2f}%")
c3.metric("Expected Volatility", f"{opt_vol*100:.2f}%")
c4.metric("Expected Sharpe", f"{opt_sharpe:.2f}")

c5, c6, c7, c8 = st.columns(4)

c5.metric("Equal Weight Return", f"{eq_return*100:.2f}%")
c6.metric("Equal Weight Volatility", f"{eq_vol*100:.2f}%")
c7.metric("Equal Weight Sharpe", f"{eq_sharpe:.2f}")
c8.metric("Assets Used", f"{len(tickers)}")

st.divider()


# =============================
# Insight
# =============================
section(
    "Optimizer Insight",
    "Plain-English interpretation of optimized portfolio quality."
)

if opt_sharpe > eq_sharpe:
    st.success("The optimized portfolio has a higher Sharpe ratio than the equal-weight benchmark.")

elif opt_sharpe < eq_sharpe:
    st.warning("The equal-weight portfolio has a higher Sharpe ratio than the optimized portfolio under current settings.")

else:
    st.info("The optimized and equal-weight portfolios have similar Sharpe ratios.")

st.divider()


# =============================
# Optimized weights
# =============================
section(
    "Optimized Weights",
    "Suggested portfolio allocation from the selected optimization method."
)

st.dataframe(
    opt_weight_df,
    use_container_width=True
)

st.divider()


# =============================
# Weight comparison
# =============================
section(
    "Weight Comparison",
    "Visual comparison between optimized and equal-weight portfolios."
)

col1, col2 = st.columns(2)

with col1:
    fig1 = create_weight_bar_chart(
        opt_weight_df,
        f"{method} Weights"
    )

    st.pyplot(fig1)

with col2:
    fig2 = create_weight_bar_chart(
        eq_weight_df,
        "Equal Weight Portfolio"
    )

    st.pyplot(fig2)

st.divider()


# =============================
# Efficient cloud
# =============================
section(
    "Efficient Cloud",
    "Randomly simulated portfolios showing the risk-return opportunity set."
)

cloud_df = simulate_efficient_cloud(
    mean_returns,
    cov_matrix,
    n_points=1200
)

fig3, ax3 = plt.subplots(figsize=(10, 5))

ax3.scatter(
    cloud_df["Volatility"] * 100,
    cloud_df["Return"] * 100,
    alpha=0.35,
    s=12
)

ax3.scatter(
    [opt_vol * 100],
    [opt_return * 100],
    s=120,
    marker="x",
    label=method
)

ax3.scatter(
    [eq_vol * 100],
    [eq_return * 100],
    s=120,
    marker="o",
    label="Equal Weight"
)

ax3.set_xlabel("Volatility %")
ax3.set_ylabel("Expected Return %")
ax3.set_title("Portfolio Opportunity Set")
ax3.legend()

st.pyplot(fig3)

st.divider()


# =============================
# Asset statistics
# =============================
section(
    "Asset Statistics",
    "Individual asset return, volatility, and allocation details."
)

asset_rows = []

j = 0
while j < len(tickers):
    t = tickers[j]

    col = returns_df[t].dropna()

    asset_rows.append({
        "Ticker": t,
        "Annual Return %": float(col.mean() * 252 * 100),
        "Annual Volatility %": float(col.std() * np.sqrt(252) * 100),
        "Optimized Weight %": float(opt_weights[j] * 100),
        "Equal Weight %": float(eq_weights[j] * 100)
    })

    j += 1

asset_stats_df = pd.DataFrame(asset_rows)

asset_stats_df = (
    asset_stats_df
    .sort_values("Optimized Weight %", ascending=False)
)

st.dataframe(
    asset_stats_df,
    use_container_width=True
)

st.divider()


# =============================
# Notes
# =============================
section(
    "Method Notes",
    "Important assumptions behind this optimizer."
)

st.write("This optimizer uses historical returns and covariance from Yahoo Finance price data.")
st.write("Max Sharpe and Minimum Volatility use random search over many long-only portfolios.")
st.write("Risk Parity uses inverse-volatility weighting as a simple approximation.")
st.write("This is educational tooling, not financial advice.")


# =============================
# Next step
# =============================
next_step(
    "Use Trading Sim or Risk Engine next to compare the optimized portfolio against your current simulated holdings."
)