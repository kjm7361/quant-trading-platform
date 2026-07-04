import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

from components.layout import setup_page, section, next_step, plotly_config


# =============================
# Page setup
# =============================
setup_page(
    "Execution Engine",
    "Institutional-style execution simulator with market impact, TWAP, VWAP, and adaptive execution logic.",
    "⚡"
)


# -----------------------------
# Helpers
# -----------------------------
def load_prices(symbol: str, period: str = "5d", interval: str = "5m") -> pd.DataFrame:
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
        if symbol in data.columns.get_level_values(-1):
            data = data.xs(symbol, axis=1, level=-1)

        elif "Close" in data.columns.get_level_values(0):
            data.columns = data.columns.get_level_values(0)

    needed_cols = ["Open", "High", "Low", "Close", "Volume"]

    fixed = pd.DataFrame(index=data.index)

    for col in needed_cols:
        if col in data.columns:
            fixed[col] = pd.to_numeric(data[col], errors="coerce")

        else:
            if col == "Volume":
                fixed[col] = 0.0
            else:
                fixed[col] = np.nan

    fixed = fixed.dropna(subset=["Close"]).copy()
    fixed["Volume"] = fixed["Volume"].fillna(0.0)

    return fixed


def build_intraday_volume_curve(n: int) -> np.ndarray:
    if n <= 1:
        return np.array([1.0])

    x = np.linspace(-1, 1, n)

    curve = 1.35 - 0.65 * (1 - x**2)
    curve = np.maximum(curve, 0.1)
    curve = curve / curve.sum()

    return curve


def estimate_volatility(close: pd.Series) -> float:
    rets = close.pct_change().dropna()

    if len(rets) == 0:
        return 0.0

    return float(rets.std())


def estimate_avg_volume(volume: pd.Series) -> float:
    if len(volume) == 0:
        return 0.0

    return float(volume.mean())


def compute_imbalance_series(df: pd.DataFrame) -> pd.Series:
    spread_proxy = (df["High"] - df["Low"]).replace(0, np.nan)

    close_location = ((df["Close"] - df["Low"]) / spread_proxy).fillna(0.5)

    imbalance = (close_location - 0.5) * 2
    imbalance = imbalance.clip(-1, 1)

    return imbalance


def build_schedule(style: str, total_shares: int, n_steps: int, volume_curve: np.ndarray) -> np.ndarray:

    if total_shares <= 0 or n_steps <= 0:
        return np.array([])

    if style == "Immediate":
        sched = np.zeros(n_steps)
        sched[0] = total_shares
        return sched

    if style == "TWAP":
        raw = np.ones(n_steps) / n_steps

    elif style == "VWAP":
        raw = volume_curve.copy()

    else:
        raw = np.ones(n_steps) / n_steps

    raw = raw / raw.sum()

    sched = raw * total_shares

    rounded = np.floor(sched).astype(int)

    remainder = total_shares - int(rounded.sum())

    if remainder > 0:
        fractional = sched - rounded
        idx = np.argsort(-fractional)

        for i in range(remainder):
            rounded[idx[i % len(idx)]] += 1

    return rounded


def build_adaptive_schedule(
    total_shares: int,
    n_steps: int,
    volume_curve: np.ndarray,
    imbalance: pd.Series,
    volatility: float,
    aggression: float
) -> np.ndarray:

    if total_shares <= 0 or n_steps <= 0:
        return np.array([])

    imb = imbalance.values[:n_steps]

    if len(imb) < n_steps:
        padded = np.zeros(n_steps)
        padded[:len(imb)] = imb
        imb = padded

    base = volume_curve.copy()

    favorable = 1 + aggression * np.maximum(imb, 0)
    unfavorable = 1 - 0.6 * aggression * np.maximum(-imb, 0)

    vol_penalty = np.ones(n_steps)

    if volatility > 0:
        vol_penalty = np.clip(
            1.0 - min(volatility * 25, 0.4),
            0.6,
            1.0
        )

    raw = base * favorable * unfavorable * vol_penalty

    raw = np.maximum(raw, 0.001)
    raw = raw / raw.sum()

    sched = raw * total_shares

    rounded = np.floor(sched).astype(int)

    remainder = total_shares - int(rounded.sum())

    if remainder > 0:
        fractional = sched - rounded
        idx = np.argsort(-fractional)

        for i in range(remainder):
            rounded[idx[i % len(idx)]] += 1

    return rounded


def simulate_execution(
    df: pd.DataFrame,
    shares_schedule: np.ndarray,
    side: str,
    impact_k: float,
    fixed_fee: float,
    noise_scale: float,
    seed: int
):

    np.random.seed(seed)

    close = df["Close"].values

    volume = (
        df["Volume"]
        .replace(0, np.nan)
        .fillna(df["Volume"].mean() if df["Volume"].mean() > 0 else 1)
        .values
    )

    n_steps = min(len(close), len(shares_schedule))

    sign = 1 if side == "Buy" else -1

    rows = []

    total_cost = 0.0
    total_signed_shares = 0
    total_notional = 0.0

    for i in range(n_steps):

        shares = int(shares_schedule[i])

        if shares <= 0:
            rows.append({
                "step": i,
                "market_price": close[i],
                "shares": 0,
                "impact_per_share": 0.0,
                "noise": 0.0,
                "exec_price": close[i],
                "trade_notional": 0.0,
                "cum_shares": total_signed_shares,
                "cum_cost": total_cost,
            })

            continue

        participation = shares / max(volume[i], 1)

        impact = impact_k * np.sqrt(max(participation, 1e-8)) * close[i]

        noise = np.random.normal(0, noise_scale * close[i])

        exec_price = close[i] + sign * impact + sign * noise

        trade_notional = exec_price * shares

        total_notional += close[i] * shares

        if side == "Buy":
            total_cost += trade_notional + fixed_fee
            total_signed_shares += shares

        else:
            total_cost += trade_notional - fixed_fee
            total_signed_shares += shares

        rows.append({
            "step": i,
            "market_price": close[i],
            "shares": shares,
            "impact_per_share": exec_price - close[i],
            "noise": noise,
            "exec_price": exec_price,
            "trade_notional": trade_notional,
            "cum_shares": total_signed_shares,
            "cum_cost": total_cost,
        })

    result = pd.DataFrame(rows)

    executed = result[result["shares"] > 0].copy()

    if executed.empty:
        avg_exec_price = 0.0
        implementation_shortfall = 0.0
        slippage_bps = 0.0

    else:
        total_exec_shares = executed["shares"].sum()

        avg_exec_price = (
            (executed["exec_price"] * executed["shares"]).sum()
            / total_exec_shares
        )

        arrival_price = float(close[0])

        if side == "Buy":
            implementation_shortfall = (
                (avg_exec_price - arrival_price)
                * total_exec_shares
            )

            slippage_bps = (
                ((avg_exec_price / arrival_price) - 1)
                * 10000
            )

        else:
            implementation_shortfall = (
                (arrival_price - avg_exec_price)
                * total_exec_shares
            )

            slippage_bps = (
                ((arrival_price / avg_exec_price) - 1)
                * 10000
                if avg_exec_price != 0 else 0.0
            )

    return result, {
        "arrival_price": float(close[0]) if len(close) > 0 else 0.0,
        "avg_exec_price": float(avg_exec_price),
        "implementation_shortfall": float(implementation_shortfall),
        "slippage_bps": float(slippage_bps),
        "shares_executed": int(result["shares"].sum()),
        "total_cost": float(total_cost),
        "market_notional": float(total_notional),
    }


def simulate_benchmark_immediate(
    df: pd.DataFrame,
    total_shares: int,
    side: str,
    fixed_fee: float
):

    if df.empty or total_shares <= 0:
        return 0.0, 0.0

    arrival = float(df["Close"].iloc[0])

    notional = arrival * total_shares

    if side == "Buy":
        total = notional + fixed_fee

    else:
        total = notional - fixed_fee

    return arrival, total


# -----------------------------
# Sidebar controls
# -----------------------------
with st.sidebar:

    st.header("Trade Inputs")

    symbol = st.text_input("Ticker", value="NVDA").upper().strip()

    side = st.selectbox(
        "Side",
        ["Buy", "Sell"]
    )

    shares = st.number_input(
        "Order Size Shares",
        min_value=1,
        value=1000,
        step=100
    )

    execution_style = st.selectbox(
        "Execution Style",
        ["Immediate", "TWAP", "VWAP", "Adaptive"]
    )

    st.subheader("Data Settings")

    period = st.selectbox(
        "Lookback Period",
        ["1d", "5d", "1mo"],
        index=1
    )

    interval = st.selectbox(
        "Bar Interval",
        ["1m", "2m", "5m", "15m"],
        index=2
    )

    max_steps = st.slider(
        "Max Bars to Use",
        min_value=10,
        max_value=300,
        value=60,
        step=10
    )

    st.subheader("Execution Parameters")

    impact_k = st.slider(
        "Market Impact Strength",
        min_value=0.001,
        max_value=0.100,
        value=0.020,
        step=0.001
    )

    fixed_fee = st.number_input(
        "Fixed Fee Per Trade",
        min_value=0.0,
        value=1.0,
        step=0.5
    )

    noise_scale = st.slider(
        "Execution Noise",
        min_value=0.0,
        max_value=0.010,
        value=0.001,
        step=0.0005
    )

    aggression = st.slider(
        "Adaptive Aggression",
        min_value=0.0,
        max_value=2.0,
        value=1.0,
        step=0.1
    )

    seed = st.number_input(
        "Random Seed",
        min_value=0,
        value=42,
        step=1
    )

    run = st.button(
        "Run Execution Simulation",
        use_container_width=True
    )


# -----------------------------
# Waiting state
# -----------------------------
if not run:
    st.info("Choose inputs in the sidebar and click Run Execution Simulation.")
    st.stop()


# -----------------------------
# Load data
# -----------------------------
section(
    "Market Data",
    "Download intraday market data and estimate market microstructure conditions."
)

df = load_prices(
    symbol,
    period=period,
    interval=interval
)

if df.empty:
    st.error("Could not load market data. Try another ticker, interval, or period.")
    st.stop()

df = df.tail(max_steps).copy()

if len(df) < 5:
    st.error("Not enough market data returned for simulation.")
    st.stop()

df["Imbalance"] = compute_imbalance_series(df)

volatility = estimate_volatility(df["Close"])

avg_volume = estimate_avg_volume(df["Volume"])

volume_curve = build_intraday_volume_curve(len(df))

st.success("Market data loaded successfully.")

st.divider()


# -----------------------------
# Build schedule
# -----------------------------
section(
    "Execution Schedule",
    "Generate execution schedules using TWAP, VWAP, Immediate, or Adaptive logic."
)

if execution_style == "Adaptive":

    shares_schedule = build_adaptive_schedule(
        total_shares=shares,
        n_steps=len(df),
        volume_curve=volume_curve,
        imbalance=df["Imbalance"],
        volatility=volatility,
        aggression=aggression,
    )

else:
    shares_schedule = build_schedule(
        style=execution_style,
        total_shares=shares,
        n_steps=len(df),
        volume_curve=volume_curve,
    )

sim_result, stats = simulate_execution(
    df=df,
    shares_schedule=shares_schedule,
    side=side,
    impact_k=impact_k,
    fixed_fee=fixed_fee,
    noise_scale=noise_scale,
    seed=int(seed),
)

arrival_price, naive_total = simulate_benchmark_immediate(
    df=df,
    total_shares=shares,
    side=side,
    fixed_fee=fixed_fee,
)

if side == "Buy":
    savings = naive_total - stats["total_cost"]

else:
    savings = stats["total_cost"] - naive_total


# -----------------------------
# Top metrics
# -----------------------------
section(
    "Execution Metrics",
    "Institutional execution quality metrics and slippage analysis."
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Arrival Price", f"${stats['arrival_price']:.2f}")
c2.metric("Average Execution Price", f"${stats['avg_exec_price']:.2f}")
c3.metric("Slippage", f"{stats['slippage_bps']:.2f} bps")
c4.metric(
    "Implementation Shortfall",
    f"${stats['implementation_shortfall']:,.2f}"
)

c5, c6, c7, c8 = st.columns(4)

c5.metric("Shares Executed", f"{stats['shares_executed']:,}")
c6.metric("Average Bar Volume", f"{avg_volume:,.0f}")
c7.metric("Estimated Volatility", f"{volatility:.4f}")
c8.metric("Savings vs Immediate", f"${savings:,.2f}")

st.divider()


# -----------------------------
# Summary
# -----------------------------
section(
    "Execution Summary",
    "Overview of execution configuration and simulation setup."
)

summary_text = f"""
Ticker: {symbol}  
Side: {side}  
Order Size: {shares:,} shares  
Execution Style: {execution_style}  
Bars Used: {len(df)}  
"""

st.markdown(summary_text)

st.divider()


# -----------------------------
# Price chart
# -----------------------------
section(
    "Price Path and Executions",
    "Market price path with simulated execution points."
)

exec_points = sim_result[sim_result["shares"] > 0].copy()

fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines",
                          name="Market Price", line=dict(color="#10b981", width=2)))
if not exec_points.empty:
    marker_sizes = np.maximum(
        exec_points["shares"] / max(exec_points["shares"].max(), 1) * 20, 8
    )
    fig1.add_trace(go.Scatter(
        x=df.index[exec_points["step"]],
        y=exec_points["exec_price"],
        mode="markers",
        name="Execution Points",
        marker=dict(color="#f59e0b", size=marker_sizes, opacity=0.8),
    ))
fig1.update_layout(title=f"{symbol} Market Price vs Execution Prices",
                   xaxis_title="Time", yaxis_title="Price", **plotly_config())
st.plotly_chart(fig1, use_container_width=True)

st.divider()


# -----------------------------
# Schedule chart
# -----------------------------
section(
    "Execution Schedule Distribution",
    "Shares traded per execution interval."
)

fig2 = go.Figure(go.Bar(x=list(range(len(shares_schedule))), y=shares_schedule,
                        marker_color="#3b82f6"))
fig2.update_layout(title="Shares Traded Per Bar", xaxis_title="Bar", yaxis_title="Shares",
                   **plotly_config())
st.plotly_chart(fig2, use_container_width=True)

st.divider()


# -----------------------------
# Cost chart
# -----------------------------
section(
    "Cumulative Execution Cost",
    "Track cumulative execution cost through time."
)

fig3 = go.Figure(go.Scatter(x=sim_result["step"], y=sim_result["cum_cost"],
                            mode="lines", line=dict(color="#10b981", width=2)))
fig3.update_layout(title="Cumulative Cost Through Time", xaxis_title="Bar",
                   yaxis_title="Cumulative Cost", **plotly_config())
st.plotly_chart(fig3, use_container_width=True)

st.divider()


# -----------------------------
# Market impact chart
# -----------------------------
section(
    "Per-Trade Market Impact",
    "Execution premium or discount versus prevailing market price."
)

impact_only = sim_result[sim_result["shares"] > 0].copy()

fig4 = go.Figure()
if not impact_only.empty:
    fig4.add_trace(go.Bar(x=impact_only["step"], y=impact_only["impact_per_share"],
                          marker_color="#ef4444"))
fig4.update_layout(title="Execution Premium / Discount vs Market Price",
                   xaxis_title="Bar", yaxis_title="Impact Per Share", **plotly_config())
st.plotly_chart(fig4, use_container_width=True)

st.divider()


# -----------------------------
# Strategy comparison
# -----------------------------
section(
    "Strategy Comparison",
    "Compare advanced execution versus naive immediate execution."
)

comparison_df = pd.DataFrame({
    "Method": [
        "Immediate Benchmark",
        execution_style
    ],
    "Total Dollar Cost": [
        naive_total,
        stats["total_cost"]
    ],
    "Average Price": [
        arrival_price,
        stats["avg_exec_price"]
    ],
    "Shares": [
        shares,
        stats["shares_executed"]
    ],
})

st.dataframe(
    comparison_df,
    use_container_width=True
)

st.divider()


# -----------------------------
# Trade log
# -----------------------------
section(
    "Detailed Trade Log",
    "Granular simulated execution-level data."
)

trade_log = sim_result.copy()

trade_log["timestamp"] = df.index[trade_log["step"]].values

trade_log = trade_log[
    [
        "timestamp",
        "step",
        "market_price",
        "shares",
        "exec_price",
        "impact_per_share",
        "trade_notional",
        "cum_shares",
        "cum_cost",
    ]
]

st.dataframe(
    trade_log,
    use_container_width=True
)

st.divider()


# -----------------------------
# Download
# -----------------------------
section(
    "Export Results",
    "Download simulated execution trade logs."
)

csv = trade_log.to_csv(index=False).encode("utf-8")

st.download_button(
    "Download Trade Log CSV",
    data=csv,
    file_name=f"{symbol.lower()}_execution_log.csv",
    mime="text/csv",
)

# -----------------------------
# Insight
# -----------------------------
section("Execution Insight")

if savings > 0:
    st.success(
        f"{execution_style} execution reduced estimated execution cost versus naive immediate execution."
    )

elif savings < 0:
    st.warning(
        f"{execution_style} execution performed worse than naive immediate execution under current parameters."
    )

else:
    st.info("Execution cost was similar to immediate execution.")

next_step(
    "Use Trading Sim or Risk Engine next to understand how execution quality affects portfolio performance and drawdown."
)