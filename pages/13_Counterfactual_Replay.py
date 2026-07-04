import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

from components.layout import setup_page, section, next_step, plotly_config

from execution.sim_broker import list_trades


# =============================
# Page setup
# =============================
setup_page(
    "Counterfactual Replay Engine",
    "Replay historical trades under alternate decisions and compare hypothetical outcomes.",
    "🕰️"
)


# =============================
# Helpers
# =============================
def load_price_data(symbols, period="1mo", interval="1d"):

    clean_symbols = []

    i = 0
    while i < len(symbols):

        s = str(symbols[i]).upper().strip()

        if s != "" and s not in clean_symbols:
            clean_symbols.append(s)

        i += 1

    if len(clean_symbols) == 0:
        return pd.DataFrame()

    try:

        data = yf.download(
            clean_symbols,
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

                close_df[clean_symbols[0]] = pd.to_numeric(
                    data["Close"],
                    errors="coerce"
                )

            else:
                return pd.DataFrame()

        close_df = (
            close_df
            .sort_index()
            .ffill()
            .dropna(how="all")
        )

        return close_df

    except:
        return pd.DataFrame()


def build_trade_df(trades):

    rows = []

    i = 0

    while i < len(trades):

        t = trades[i]

        rows.append({
            "time": pd.to_datetime(t["ts"], unit="s"),
            "symbol": str(t["symbol"]).upper().strip(),
            "side": str(t["side"]).lower().strip(),
            "qty": float(t["qty"]),
            "price": float(t["price"]),
            "ts": int(t["ts"])
        })

        i += 1

    if len(rows) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    df = (
        df
        .sort_values("time")
        .reset_index(drop=True)
    )

    return df


def nearest_price_at_or_after(price_series, trade_time):

    if len(price_series) == 0:
        return None, None

    idx = list(price_series.index)
    vals = list(price_series.values)

    i = 0

    while i < len(idx):

        if pd.Timestamp(idx[i]) >= pd.Timestamp(trade_time):
            return pd.Timestamp(idx[i]), float(vals[i])

        i += 1

    return pd.Timestamp(idx[-1]), float(vals[-1])


def nearest_price_with_delay(price_series, trade_time, delay_bars):

    if len(price_series) == 0:
        return None, None

    idx = list(price_series.index)
    vals = list(price_series.values)

    start_pos = None

    i = 0

    while i < len(idx):

        if pd.Timestamp(idx[i]) >= pd.Timestamp(trade_time):
            start_pos = i
            break

        i += 1

    if start_pos is None:
        start_pos = len(idx) - 1

    pos = start_pos + int(delay_bars)

    if pos >= len(idx):
        pos = len(idx) - 1

    return pd.Timestamp(idx[pos]), float(vals[pos])


def transform_trades(
    trades_df,
    price_df,
    scenario_name,
    delay_bars=0,
    size_multiplier=1.0,
    skip_indices=None
):

    if trades_df.empty or price_df.empty:
        return pd.DataFrame()

    if skip_indices is None:
        skip_indices = []

    transformed = []

    i = 0

    while i < len(trades_df):

        if i in skip_indices:
            i += 1
            continue

        row = trades_df.iloc[i]

        sym = row["symbol"]

        if sym not in price_df.columns:
            i += 1
            continue

        series = price_df[sym].dropna()

        if len(series) == 0:
            i += 1
            continue

        if delay_bars > 0:

            exec_time, exec_price = nearest_price_with_delay(
                series,
                row["time"],
                delay_bars
            )

        else:

            exec_time, exec_price = nearest_price_at_or_after(
                series,
                row["time"]
            )

        if exec_time is None or exec_price is None:
            i += 1
            continue

        new_qty = float(row["qty"]) * float(size_multiplier)

        transformed.append({
            "time": exec_time,
            "symbol": sym,
            "side": row["side"],
            "qty": new_qty,
            "price": exec_price,
            "scenario": scenario_name,
            "original_index": i
        })

        i += 1

    if len(transformed) == 0:
        return pd.DataFrame()

    out = pd.DataFrame(transformed)

    out = (
        out
        .sort_values("time")
        .reset_index(drop=True)
    )

    return out


def equity_curve_from_trade_df(
    trade_df,
    price_df,
    starting_cash=100000.0
):

    if trade_df.empty or price_df.empty:
        return pd.Series(dtype=float)

    symbols = list(price_df.columns)

    holdings = {}

    i = 0

    while i < len(symbols):
        holdings[symbols[i]] = 0.0
        i += 1

    cash = float(starting_cash)

    equity_values = []

    trade_ptr = 0

    n_trades = len(trade_df)

    time_index = list(price_df.index)

    t = 0

    while t < len(time_index):

        current_time = pd.Timestamp(time_index[t])

        while (
            trade_ptr < n_trades and
            pd.Timestamp(trade_df.loc[trade_ptr, "time"]) <= current_time
        ):

            tr = trade_df.loc[trade_ptr]

            sym = tr["symbol"]
            side = tr["side"]
            qty = float(tr["qty"])
            px = float(tr["price"])

            if side == "buy":
                cash -= qty * px
                holdings[sym] += qty

            elif side == "sell":
                cash += qty * px
                holdings[sym] -= qty

            trade_ptr += 1

        equity_now = cash

        s = 0

        while s < len(symbols):

            sym = symbols[s]

            px = price_df.loc[current_time, sym]

            if pd.notna(px):
                equity_now += holdings[sym] * float(px)

            s += 1

        equity_values.append(equity_now)

        t += 1

    eq = pd.Series(
        equity_values,
        index=price_df.index
    )

    eq = eq.dropna()

    return eq


def summarize_equity(eq, starting_cash=100000.0):

    if len(eq) < 2:
        return {
            "ending_value": starting_cash,
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "volatility": 0.0,
            "sharpe": 0.0
        }

    rets = eq.pct_change().dropna()

    dd = eq / eq.cummax() - 1

    vol = float(rets.std()) if len(rets) > 1 else 0.0

    sharpe = 0.0

    if vol > 0:
        sharpe = float(
            (rets.mean() / (vol + 1e-9))
            * np.sqrt(252)
        )

    return {
        "ending_value": float(eq.iloc[-1]),
        "total_return": float((eq.iloc[-1] / float(starting_cash)) - 1),
        "max_drawdown": float(dd.min()),
        "volatility": vol,
        "sharpe": sharpe
    }


def estimate_trade_pnl(trades_df):

    if trades_df.empty:
        return pd.Series(dtype=float)

    pnl_vals = []

    i = 0

    while i < len(trades_df):

        row = trades_df.iloc[i]

        sign = 1.0 if row["side"] == "sell" else -1.0

        pnl_vals.append(
            sign
            * float(row["qty"])
            * float(row["price"])
        )

        i += 1

    return pd.Series(pnl_vals)


# =============================
# Sidebar settings
# =============================
st.sidebar.header("Replay Settings")

starting_cash = st.sidebar.number_input(
    "Starting Cash ($)",
    min_value=1000.0,
    value=100000.0,
    step=1000.0
)

period = st.sidebar.selectbox(
    "Historical Period",
    ["1mo", "3mo", "6mo"],
    index=0
)

interval = st.sidebar.selectbox(
    "Historical Interval",
    ["1d", "1h"],
    index=0
)

scenario = st.sidebar.selectbox(
    "Counterfactual Scenario",
    [
        "Actual",
        "Delay Every Trade",
        "Half Position Size",
        "Skip Worst 3 Trades",
        "Delay + Half Size"
    ],
    index=1
)

delay_bars = st.sidebar.slider(
    "Delay Bars",
    1,
    10,
    2
)

size_multiplier = st.sidebar.slider(
    "Position Size Multiplier",
    0.1,
    1.5,
    0.5,
    0.1
)

run = st.sidebar.button(
    "Run Replay",
    use_container_width=True
)


# =============================
# Waiting state
# =============================
if not run:
    st.info("Choose a replay scenario in the sidebar and click Run Replay.")
    st.stop()


# =============================
# Load trades
# =============================
section(
    "Trade History",
    "Load historical simulated trades for replay analysis."
)

raw_trades = list_trades(limit=200)

trades_df = build_trade_df(raw_trades)

if trades_df.empty:
    st.warning("No trade history found. Place trades in Trading Sim first.")
    st.stop()

symbols = list(
    trades_df["symbol"]
    .dropna()
    .unique()
)

price_df = load_price_data(
    symbols,
    period=period,
    interval=interval
)

if price_df.empty:
    st.error("Could not load historical prices for replay.")
    st.stop()

st.success(f"Loaded {len(trades_df)} historical trades.")

st.divider()


# =============================
# Build actual replay
# =============================
actual_trade_df = transform_trades(
    trades_df=trades_df,
    price_df=price_df,
    scenario_name="Actual",
    delay_bars=0,
    size_multiplier=1.0,
    skip_indices=[]
)

if actual_trade_df.empty:
    st.warning("Could not align actual trades to historical market data.")
    st.stop()


# =============================
# Counterfactual scenarios
# =============================
skip_list = []

if scenario == "Skip Worst 3 Trades":

    trade_pnl_proxy = estimate_trade_pnl(trades_df)

    if len(trade_pnl_proxy) > 0:

        worst_idx = list(
            trade_pnl_proxy
            .sort_values()
            .index[:3]
        )

        skip_list = worst_idx


if scenario == "Actual":

    counterfactual_trade_df = actual_trade_df.copy()

elif scenario == "Delay Every Trade":

    counterfactual_trade_df = transform_trades(
        trades_df=trades_df,
        price_df=price_df,
        scenario_name=scenario,
        delay_bars=delay_bars,
        size_multiplier=1.0,
        skip_indices=[]
    )

elif scenario == "Half Position Size":

    counterfactual_trade_df = transform_trades(
        trades_df=trades_df,
        price_df=price_df,
        scenario_name=scenario,
        delay_bars=0,
        size_multiplier=0.5,
        skip_indices=[]
    )

elif scenario == "Skip Worst 3 Trades":

    counterfactual_trade_df = transform_trades(
        trades_df=trades_df,
        price_df=price_df,
        scenario_name=scenario,
        delay_bars=0,
        size_multiplier=1.0,
        skip_indices=skip_list
    )

else:

    counterfactual_trade_df = transform_trades(
        trades_df=trades_df,
        price_df=price_df,
        scenario_name=scenario,
        delay_bars=delay_bars,
        size_multiplier=size_multiplier,
        skip_indices=[]
    )

if counterfactual_trade_df.empty:
    st.warning("Counterfactual scenario produced no usable trades.")
    st.stop()


# =============================
# Build equity curves
# =============================
actual_eq = equity_curve_from_trade_df(
    actual_trade_df,
    price_df,
    starting_cash=starting_cash
)

counter_eq = equity_curve_from_trade_df(
    counterfactual_trade_df,
    price_df,
    starting_cash=starting_cash
)

actual_stats = summarize_equity(
    actual_eq,
    starting_cash=starting_cash
)

counter_stats = summarize_equity(
    counter_eq,
    starting_cash=starting_cash
)

delta_return = (
    counter_stats["total_return"]
    - actual_stats["total_return"]
)

delta_dd = (
    counter_stats["max_drawdown"]
    - actual_stats["max_drawdown"]
)

delta_sharpe = (
    counter_stats["sharpe"]
    - actual_stats["sharpe"]
)


# =============================
# Scenario comparison
# =============================
section(
    "Scenario Comparison",
    "Compare the original strategy against the counterfactual replay."
)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Actual Ending Value",
    f"${actual_stats['ending_value']:,.2f}"
)

c2.metric(
    "Counterfactual Ending Value",
    f"${counter_stats['ending_value']:,.2f}"
)

c3.metric(
    "Return Difference",
    f"{delta_return*100:.2f}%"
)

c4.metric(
    "Sharpe Difference",
    f"{delta_sharpe:.2f}"
)

c5, c6, c7, c8 = st.columns(4)

c5.metric(
    "Actual Max Drawdown",
    f"{actual_stats['max_drawdown']*100:.2f}%"
)

c6.metric(
    "Counterfactual Max Drawdown",
    f"{counter_stats['max_drawdown']*100:.2f}%"
)

c7.metric(
    "Drawdown Change",
    f"{delta_dd*100:.2f}%"
)

c8.metric(
    "Scenario",
    scenario
)

st.divider()


# =============================
# Replay summary
# =============================
section(
    "Replay Summary",
    "Description of the selected alternate reality scenario."
)

if scenario == "Delay Every Trade":

    st.info(
        f"This scenario delays every trade by {delay_bars} historical bars."
    )

elif scenario == "Half Position Size":

    st.info(
        "This scenario cuts every trade to 50% of original size."
    )

elif scenario == "Skip Worst 3 Trades":

    st.info(
        "This scenario removes the three worst proxy trades from replay."
    )

elif scenario == "Delay + Half Size":

    st.info(
        f"This scenario delays every trade by {delay_bars} bars and scales size by {size_multiplier:.1f}x."
    )

else:

    st.info(
        "This is the baseline replay using original trade timing and size."
    )

st.divider()


# =============================
# Equity comparison
# =============================
section(
    "Equity Curve Comparison",
    "Compare portfolio evolution under different decisions."
)

eq_compare = pd.DataFrame({
    "Actual": actual_eq,
    "Counterfactual": counter_eq
}).dropna(how="all")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=eq_compare.index.tolist(),
    y=eq_compare["Actual"].tolist(),
    mode="lines",
    name="Actual",
    line=dict(color="#10b981", width=2)
))
fig.add_trace(go.Scatter(
    x=eq_compare.index.tolist(),
    y=eq_compare["Counterfactual"].tolist(),
    mode="lines",
    name="Counterfactual",
    line=dict(color="#3b82f6", width=2)
))
fig.update_layout(title="Equity Curve Comparison", xaxis_title="Date", yaxis_title="Portfolio Value", **plotly_config())
st.plotly_chart(fig, use_container_width=True)

st.divider()


# =============================
# Performance table
# =============================
section(
    "Performance Table",
    "Detailed performance comparison between actual and alternate execution."
)

perf_df = pd.DataFrame({
    "Metric": [
        "Ending Value",
        "Total Return",
        "Max Drawdown",
        "Volatility",
        "Sharpe"
    ],
    "Actual": [
        f"${actual_stats['ending_value']:,.2f}",
        f"{actual_stats['total_return']*100:.2f}%",
        f"{actual_stats['max_drawdown']*100:.2f}%",
        f"{actual_stats['volatility']:.4f}",
        f"{actual_stats['sharpe']:.2f}"
    ],
    "Counterfactual": [
        f"${counter_stats['ending_value']:,.2f}",
        f"{counter_stats['total_return']*100:.2f}%",
        f"{counter_stats['max_drawdown']*100:.2f}%",
        f"{counter_stats['volatility']:.4f}",
        f"{counter_stats['sharpe']:.2f}"
    ]
})

st.dataframe(
    perf_df,
    use_container_width=True
)

st.divider()


# =============================
# Trade count comparison
# =============================
section(
    "Trade Count Comparison",
    "Compare the number of trades between scenarios."
)

t1, t2, t3 = st.columns(3)

t1.metric(
    "Actual Trades",
    f"{len(actual_trade_df)}"
)

t2.metric(
    "Counterfactual Trades",
    f"{len(counterfactual_trade_df)}"
)

t3.metric(
    "Trades Removed",
    f"{len(actual_trade_df) - len(counterfactual_trade_df)}"
)

st.divider()


# =============================
# Replay insight
# =============================
section(
    "Replay Insight",
    "Interpretation of the alternate decision path."
)

if delta_return > 0:
    st.success(
        "The counterfactual scenario improved overall returns relative to the original trades."
    )

elif delta_return < 0:
    st.warning(
        "The alternate decisions reduced overall returns relative to the original trades."
    )

else:
    st.info(
        "The alternate scenario produced similar performance to the original trades."
    )

st.divider()


# =============================
# Actual trades
# =============================
section(
    "Actual Replay Trades",
    "Trades replayed using the original execution assumptions."
)

show_actual = actual_trade_df.copy()

show_actual["time"] = show_actual["time"].astype(str)

st.dataframe(
    show_actual,
    use_container_width=True
)

st.divider()


# =============================
# Counterfactual trades
# =============================
section(
    "Counterfactual Replay Trades",
    "Trades replayed using alternate execution assumptions."
)

show_counter = counterfactual_trade_df.copy()

show_counter["time"] = show_counter["time"].astype(str)

st.dataframe(
    show_counter,
    use_container_width=True
)

next_step(
    "Use Strategy DNA or Monte Carlo next to understand whether better execution decisions improve long-term robustness."
)
