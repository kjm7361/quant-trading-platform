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
    "Strategy DNA + Market Regime Fingerprint",
    "Analyze how your strategy behaves across different market environments and volatility regimes.",
    "🧬"
)


# =============================
# Helpers
# =============================
def load_market_data(symbol="SPY", period="1y", interval="1d"):
    try:
        data = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False
        )

        if data is None or data.empty:
            return pd.Series(dtype=float)

        if isinstance(data.columns, pd.MultiIndex):

            if "Close" in data.columns.get_level_values(0):
                close = data["Close"]

                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]

            else:
                return pd.Series(dtype=float)

        else:
            if "Close" in data.columns:
                close = data["Close"]

            else:
                return pd.Series(dtype=float)

        close = pd.to_numeric(
            close,
            errors="coerce"
        ).dropna()

        return close

    except:
        return pd.Series(dtype=float)


def safe_sharpe(x):
    x = pd.Series(x).dropna()

    if len(x) < 2 or x.std() == 0:
        return 0.0

    return float(
        (x.mean() / (x.std() + 1e-9))
        * np.sqrt(252)
    )


def safe_beta(strategy_returns, market_returns):

    df = pd.concat(
        [strategy_returns, market_returns],
        axis=1
    ).dropna()

    if len(df) < 2:
        return 0.0

    s = df.iloc[:, 0]
    m = df.iloc[:, 1]

    var_m = float(np.var(m))

    if var_m == 0:
        return 0.0

    cov = float(np.cov(s, m)[0, 1])

    return cov / var_m


def max_drawdown(equity):
    equity = pd.Series(equity).dropna()

    if len(equity) == 0:
        return 0.0

    dd = equity / equity.cummax() - 1

    return float(dd.min())


def classify_strategy(
    beta,
    up_capture,
    down_capture,
    vol_sensitivity,
    win_rate
):

    labels = []

    if beta > 0.8:
        labels.append("High-Beta")

    elif beta < 0.2:
        labels.append("Defensive")

    if up_capture > 1.0 and down_capture > 0.8:
        labels.append("Trend-Following")

    elif up_capture < 0.8 and down_capture < 0.8:
        labels.append("Low-Participation")

    elif down_capture < 0.6:
        labels.append("Downside-Resilient")

    if vol_sensitivity < -0.1:
        labels.append("Volatility-Sensitive")

    elif vol_sensitivity > 0.1:
        labels.append("Volatility-Positive")

    if 0.45 <= win_rate <= 0.6:
        labels.append("Conviction-Based")

    elif win_rate > 0.6:
        labels.append("High-Hit-Rate")

    if len(labels) == 0:
        labels.append("Balanced")

    return labels


def summarize_dna(
    labels,
    bull_sharpe,
    bear_sharpe,
    high_vol_sharpe,
    low_vol_sharpe
):

    style_text = ", ".join(labels)

    if bull_sharpe > bear_sharpe:
        market_pref = "performs better in rising markets"

    elif bear_sharpe > bull_sharpe:
        market_pref = "holds up better in falling markets"

    else:
        market_pref = "behaves similarly across bull and bear periods"

    if low_vol_sharpe > high_vol_sharpe:
        vol_pref = "works best in calmer market conditions"

    elif high_vol_sharpe > low_vol_sharpe:
        vol_pref = "benefits from volatile environments"

    else:
        vol_pref = "has similar performance across volatility regimes"

    return (
        f"This strategy behaves like a {style_text} system. "
        f"It {market_pref} and {vol_pref}."
    )


# =============================
# Load strategy data
# =============================
strategy_returns = st.session_state.get("strategy_returns", None)
equity_curve = st.session_state.get("equity_curve", None)

if strategy_returns is None or equity_curve is None or len(equity_curve) == 0:
    st.warning("No strategy data found. Run the Trading Sim, Backtest, or Performance page first.")
    st.stop()

strategy_returns = pd.Series(strategy_returns).dropna()
equity_curve = pd.Series(equity_curve).dropna()

if len(strategy_returns) < 5 or len(equity_curve) < 5:
    st.warning("Not enough strategy history yet. Generate more returns first.")
    st.stop()


# =============================
# Sidebar settings
# =============================
with st.sidebar:

    st.header("DNA Settings")

    benchmark_symbol = st.text_input(
        "Benchmark Symbol",
        value="SPY"
    )

    market_period = st.selectbox(
        "Market Lookback",
        ["6mo", "1y", "2y"],
        index=1
    )

    market_interval = st.selectbox(
        "Market Interval",
        ["1d", "1wk"],
        index=0
    )


# =============================
# Load benchmark data
# =============================
section(
    "Benchmark Data",
    "Load market benchmark returns for regime analysis."
)

market_close = load_market_data(
    benchmark_symbol,
    period=market_period,
    interval=market_interval
)

if len(market_close) == 0:
    st.error("Could not load benchmark market data.")
    st.stop()

market_returns = market_close.pct_change().dropna()

aligned = pd.concat(
    [
        strategy_returns.rename("strategy"),
        market_returns.rename("market")
    ],
    axis=1
).dropna()

if len(aligned) < 5:
    st.warning("Not enough overlap between strategy data and benchmark data.")
    st.stop()

strategy_aligned = aligned["strategy"]
market_aligned = aligned["market"]

st.success("Benchmark data aligned successfully.")

st.divider()


# =============================
# Core DNA Metrics
# =============================
beta = safe_beta(
    strategy_aligned,
    market_aligned
)

corr = float(
    strategy_aligned.corr(market_aligned)
) if len(aligned) > 1 else 0.0

win_rate = float(
    (strategy_aligned > 0).mean()
)

avg_gain = float(
    strategy_aligned[strategy_aligned > 0].mean()
) if (strategy_aligned > 0).any() else 0.0

avg_loss = float(
    strategy_aligned[strategy_aligned < 0].mean()
) if (strategy_aligned < 0).any() else 0.0

strategy_vol = float(strategy_aligned.std())

strategy_sharpe = safe_sharpe(strategy_aligned)

strategy_dd = max_drawdown(equity_curve)

bull_mask = market_aligned > 0
bear_mask = market_aligned <= 0

bull_sharpe = safe_sharpe(strategy_aligned[bull_mask])
bear_sharpe = safe_sharpe(strategy_aligned[bear_mask])

rolling_market_vol = market_aligned.rolling(20).std()

vol_median = float(
    rolling_market_vol.median()
) if len(rolling_market_vol.dropna()) > 0 else 0.0

high_vol_mask = rolling_market_vol >= vol_median
low_vol_mask = rolling_market_vol < vol_median

high_vol_sharpe = safe_sharpe(strategy_aligned[high_vol_mask])
low_vol_sharpe = safe_sharpe(strategy_aligned[low_vol_mask])

up_market = market_aligned[market_aligned > 0]
down_market = market_aligned[market_aligned < 0]

up_strategy = strategy_aligned.loc[up_market.index] if len(up_market) > 0 else pd.Series(dtype=float)

down_strategy = strategy_aligned.loc[down_market.index] if len(down_market) > 0 else pd.Series(dtype=float)

up_capture = float(
    up_strategy.mean() / (up_market.mean() + 1e-9)
) if len(up_market) > 0 else 0.0

down_capture = float(
    abs(down_strategy.mean()) / (abs(down_market.mean()) + 1e-9)
) if len(down_market) > 0 else 0.0

vol_alignment = pd.concat(
    [
        strategy_aligned.abs().rename("sabs"),
        rolling_market_vol.rename("mvol")
    ],
    axis=1
).dropna()

if len(vol_alignment) > 2:
    vol_sensitivity = float(
        vol_alignment["sabs"].corr(vol_alignment["mvol"])
    )

else:
    vol_sensitivity = 0.0

labels = classify_strategy(
    beta,
    up_capture,
    down_capture,
    vol_sensitivity,
    win_rate
)

dna_summary = summarize_dna(
    labels,
    bull_sharpe,
    bear_sharpe,
    high_vol_sharpe,
    low_vol_sharpe
)


# =============================
# DNA Summary
# =============================
section(
    "DNA Summary",
    "High-level behavioral fingerprint of the strategy."
)

st.info(dna_summary)

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Beta", f"{beta:.2f}")
c2.metric("Correlation", f"{corr:.2f}")
c3.metric("Win Rate", f"{win_rate*100:.2f}%")
c4.metric("Sharpe", f"{strategy_sharpe:.2f}")
c5.metric("Volatility", f"{strategy_vol:.4f}")
c6.metric("Max Drawdown", f"{strategy_dd*100:.2f}%")

st.divider()


# =============================
# Labels
# =============================
section(
    "Strategy Labels",
    "Qualitative classification of the strategy behavior."
)

st.success(", ".join(labels))

st.divider()


# =============================
# Regime Table
# =============================
section(
    "Regime Performance",
    "Performance under different market environments."
)

regime_df = pd.DataFrame({
    "Regime": [
        "Bull Market",
        "Bear Market",
        "High Volatility",
        "Low Volatility"
    ],
    "Sharpe": [
        bull_sharpe,
        bear_sharpe,
        high_vol_sharpe,
        low_vol_sharpe
    ],
    "Mean Return": [
        float(strategy_aligned[bull_mask].mean()) if bull_mask.any() else 0.0,
        float(strategy_aligned[bear_mask].mean()) if bear_mask.any() else 0.0,
        float(strategy_aligned[high_vol_mask].mean()) if high_vol_mask.any() else 0.0,
        float(strategy_aligned[low_vol_mask].mean()) if low_vol_mask.any() else 0.0
    ],
    "Win Rate": [
        float((strategy_aligned[bull_mask] > 0).mean()) if bull_mask.any() else 0.0,
        float((strategy_aligned[bear_mask] > 0).mean()) if bear_mask.any() else 0.0,
        float((strategy_aligned[high_vol_mask] > 0).mean()) if high_vol_mask.any() else 0.0,
        float((strategy_aligned[low_vol_mask] > 0).mean()) if low_vol_mask.any() else 0.0
    ]
})

st.dataframe(
    regime_df,
    use_container_width=True
)

st.divider()


# =============================
# Trait Fingerprint
# =============================
trend_score = max(0.0, min(1.5, up_capture))

defense_score = max(
    0.0,
    min(1.5, 1.0 - min(down_capture, 1.0))
)

vol_score = max(
    0.0,
    min(1.5, abs(vol_sensitivity))
)

beta_score = max(
    0.0,
    min(1.5, abs(beta))
)

consistency_score = max(
    0.0,
    min(1.5, win_rate)
)

conviction_score = max(
    0.0,
    min(1.5, abs(avg_gain / (abs(avg_loss) + 1e-9)))
)

trait_names = [
    "Trend",
    "Defense",
    "Vol Sensitivity",
    "Market Beta",
    "Consistency",
    "Conviction"
]

trait_scores = [
    trend_score,
    defense_score,
    vol_score,
    beta_score,
    consistency_score,
    conviction_score
]

section(
    "Strategy Trait Fingerprint",
    "Radar-style fingerprint of core strategy characteristics."
)

trait_df = pd.DataFrame({
    "Trait": trait_names,
    "Score": trait_scores
})

fig1, ax1 = plt.subplots(figsize=(10, 4))

ax1.bar(
    trait_df["Trait"],
    trait_df["Score"]
)

ax1.set_ylabel("Score")
ax1.set_title("Strategy Trait Fingerprint")

plt.xticks(rotation=20)

st.pyplot(fig1)

st.divider()


# =============================
# Rolling edge
# =============================
rolling_window = min(
    20,
    max(5, len(aligned) // 4)
)

rolling_alpha = (
    strategy_aligned.rolling(rolling_window).mean()
    - market_aligned.rolling(rolling_window).mean()
)

section(
    "Rolling Relative Edge",
    "Rolling strategy edge relative to the benchmark."
)

st.line_chart(
    rolling_alpha.dropna()
)

st.divider()


# =============================
# Dependency map
# =============================
section(
    "Market Dependency Map",
    "Scatter relationship between strategy returns and benchmark returns."
)

fig2, ax2 = plt.subplots(figsize=(7, 5))

ax2.scatter(
    market_aligned,
    strategy_aligned,
    alpha=0.6
)

ax2.set_xlabel(f"{benchmark_symbol} Returns")
ax2.set_ylabel("Strategy Returns")
ax2.set_title("Strategy vs Market Returns")

st.pyplot(fig2)

st.divider()


# =============================
# Failure conditions
# =============================
worst_regime = regime_df.sort_values("Sharpe").iloc[0]["Regime"]

best_regime = regime_df.sort_values(
    "Sharpe",
    ascending=False
).iloc[0]["Regime"]

failure_notes = []

if bear_sharpe < bull_sharpe:
    failure_notes.append("Performance weakens in falling markets.")

if high_vol_sharpe < low_vol_sharpe:
    failure_notes.append("Performance degrades when volatility rises.")

if beta > 1.0:
    failure_notes.append("Returns are strongly dependent on market direction.")

if win_rate < 0.45:
    failure_notes.append("Low hit-rate means the strategy relies on a few strong wins.")

if strategy_dd < -0.10:
    failure_notes.append("Drawdowns are meaningful and should be monitored carefully.")

section(
    "Best and Worst Environments",
    "Identify environments where the strategy performs best and worst."
)

b1, b2 = st.columns(2)

b1.success(f"Best Regime: {best_regime}")
b2.error(f"Worst Regime: {worst_regime}")

st.divider()

section(
    "Failure Conditions",
    "Known weaknesses and fragile environments from the historical sample."
)

if len(failure_notes) == 0:
    st.success("No major weakness detected from the current sample.")

else:
    i = 0

    while i < len(failure_notes):
        st.write(f"- {failure_notes[i]}")
        i += 1

st.divider()


# =============================
# Raw data
# =============================
section(
    "Aligned Strategy and Market Data",
    "Underlying aligned return data used for the analysis."
)

aligned_show = aligned.copy()

aligned_show["rolling_market_vol"] = rolling_market_vol.reindex(
    aligned_show.index
)

st.dataframe(
    aligned_show,
    use_container_width=True
)

next_step(
    "Use Monte Carlo or Risk Engine next to stress test how this strategy DNA behaves under future uncertainty."
)