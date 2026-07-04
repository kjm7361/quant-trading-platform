import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from components.layout import setup_page, section, next_step, plotly_config


# =============================
# Page setup
# =============================
setup_page(
    "Order Book Microstructure",
    "Simulate a limit order book, bid-ask spread, order book imbalance, microprice, liquidity depth, and market impact.",
    "📚"
)


# =============================
# Helper functions
# =============================
def build_order_book(mid_price, spread, levels, tick_size, base_size, decay):
    bid_prices = []
    ask_prices = []
    bid_sizes = []
    ask_sizes = []

    best_bid = mid_price - spread / 2
    best_ask = mid_price + spread / 2

    i = 0
    while i < levels:
        bid_price = best_bid - i * tick_size
        ask_price = best_ask + i * tick_size

        bid_size = base_size * np.exp(-decay * i) * np.random.uniform(0.75, 1.25)
        ask_size = base_size * np.exp(-decay * i) * np.random.uniform(0.75, 1.25)

        bid_prices.append(round(bid_price, 4))
        ask_prices.append(round(ask_price, 4))
        bid_sizes.append(round(bid_size, 2))
        ask_sizes.append(round(ask_size, 2))

        i += 1

    book = pd.DataFrame({
        "Bid Price": bid_prices,
        "Bid Size": bid_sizes,
        "Ask Price": ask_prices,
        "Ask Size": ask_sizes
    })

    return book


def compute_microstructure_metrics(book):
    best_bid = float(book["Bid Price"].iloc[0])
    best_ask = float(book["Ask Price"].iloc[0])

    bid_size_1 = float(book["Bid Size"].iloc[0])
    ask_size_1 = float(book["Ask Size"].iloc[0])

    spread = best_ask - best_bid
    mid = (best_bid + best_ask) / 2

    if bid_size_1 + ask_size_1 == 0:
        imbalance = 0.0
        microprice = mid
    else:
        imbalance = (bid_size_1 - ask_size_1) / (bid_size_1 + ask_size_1)
        microprice = (best_ask * bid_size_1 + best_bid * ask_size_1) / (bid_size_1 + ask_size_1)

    total_bid_depth = float(book["Bid Size"].sum())
    total_ask_depth = float(book["Ask Size"].sum())

    total_depth = total_bid_depth + total_ask_depth

    if total_depth == 0:
        total_imbalance = 0.0
    else:
        total_imbalance = (total_bid_depth - total_ask_depth) / total_depth

    return {
        "Best Bid": best_bid,
        "Best Ask": best_ask,
        "Spread": spread,
        "Mid Price": mid,
        "Microprice": microprice,
        "Top Imbalance": imbalance,
        "Total Bid Depth": total_bid_depth,
        "Total Ask Depth": total_ask_depth,
        "Total Imbalance": total_imbalance
    }


def estimate_market_impact(book, side, order_size):
    remaining = float(order_size)
    filled_value = 0.0
    filled_qty = 0.0
    levels_used = 0

    if side == "Buy":
        price_col = "Ask Price"
        size_col = "Ask Size"
    else:
        price_col = "Bid Price"
        size_col = "Bid Size"

    i = 0
    while i < len(book) and remaining > 0:
        available = float(book[size_col].iloc[i])
        price = float(book[price_col].iloc[i])

        fill_qty = min(remaining, available)

        filled_value += fill_qty * price
        filled_qty += fill_qty
        remaining -= fill_qty

        if fill_qty > 0:
            levels_used += 1

        i += 1

    if filled_qty == 0:
        avg_fill = 0.0
    else:
        avg_fill = filled_value / filled_qty

    unfilled = remaining

    return {
        "Requested Size": float(order_size),
        "Filled Size": float(filled_qty),
        "Unfilled Size": float(unfilled),
        "Average Fill Price": float(avg_fill),
        "Levels Used": levels_used
    }


def pressure_signal(top_imbalance, total_imbalance, microprice, mid):
    if top_imbalance > 0.25 and total_imbalance > 0.15 and microprice > mid:
        return "Buy Pressure"

    if top_imbalance < -0.25 and total_imbalance < -0.15 and microprice < mid:
        return "Sell Pressure"

    if abs(top_imbalance) < 0.10 and abs(total_imbalance) < 0.10:
        return "Balanced"

    return "Mixed"


def signal_message(signal):
    if signal == "Buy Pressure":
        return "Bid-side liquidity dominates. Short-term upward pressure may exist."

    if signal == "Sell Pressure":
        return "Ask-side liquidity dominates. Short-term downward pressure may exist."

    if signal == "Balanced":
        return "Order book is fairly balanced. No strong liquidity pressure."

    return "Liquidity signals are mixed. Avoid overinterpreting the book."


# =============================
# Sidebar controls
# =============================
st.sidebar.header("Order Book Settings")

# Real-parameter seed from Yahoo Finance
_ob_ticker = st.sidebar.text_input("Ticker to Seed", value="AAPL", key="ob_ticker")
if st.sidebar.button("Fetch Real Parameters"):
    try:
        import yfinance as yf
        _fi = yf.Ticker(_ob_ticker.strip().upper()).fast_info
        _mid_v = _fi.last_price
        _spread_v = max(0.01, (_fi.day_high - _fi.day_low) * 0.015)
        _base_v = max(100.0, (_fi.three_month_average_volume or 1_000_000) / 1000)
        if _mid_v is not None and _mid_v == _mid_v:
            st.session_state["ob_mid"]    = float(_mid_v)
            st.session_state["ob_spread"] = float(_spread_v)
            st.session_state["ob_base"]   = float(_base_v)
            st.sidebar.success(f"mid=${_mid_v:,.2f}  spread=${_spread_v:.3f}")
    except Exception:
        st.sidebar.warning("Fetch failed — using manual inputs.")

mid_price = st.sidebar.number_input(
    "Mid Price",
    min_value=1.0,
    value=float(st.session_state.get("ob_mid", 100.0)),
    step=1.0
)

spread = st.sidebar.number_input(
    "Bid-Ask Spread",
    min_value=0.01,
    value=float(st.session_state.get("ob_spread", 0.10)),
    step=0.01
)

levels = st.sidebar.slider(
    "Order Book Levels",
    5,
    30,
    12,
    1
)

tick_size = st.sidebar.number_input(
    "Tick Size",
    min_value=0.01,
    value=0.05,
    step=0.01
)

base_size = st.sidebar.number_input(
    "Base Level Size",
    min_value=10.0,
    value=float(st.session_state.get("ob_base", 1000.0)),
    step=50.0
)

decay = st.sidebar.slider(
    "Depth Decay",
    0.00,
    0.30,
    0.08,
    0.01
)

seed = st.sidebar.number_input(
    "Random Seed",
    min_value=0,
    value=7,
    step=1
)

st.sidebar.header("Execution Simulation")

side = st.sidebar.selectbox(
    "Order Side",
    ["Buy", "Sell"],
    index=0
)

order_size = st.sidebar.number_input(
    "Market Order Size",
    min_value=1.0,
    value=1500.0,
    step=100.0
)

run = st.sidebar.button(
    "Build Order Book",
    use_container_width=True
)


# =============================
# Waiting state
# =============================
if not run:
    st.info("Set order book parameters and click Build Order Book.")
    st.stop()


# =============================
# Build book
# =============================
np.random.seed(int(seed))

section(
    "Synthetic Limit Order Book",
    "A simulated order book with bid and ask levels around the mid price."
)

book = build_order_book(
    mid_price=mid_price,
    spread=spread,
    levels=levels,
    tick_size=tick_size,
    base_size=base_size,
    decay=decay
)

st.dataframe(book, use_container_width=True)

st.divider()


# =============================
# Metrics
# =============================
section(
    "Microstructure Metrics",
    "Core market microstructure metrics calculated from the order book."
)

metrics = compute_microstructure_metrics(book)

m1, m2, m3, m4 = st.columns(4)

m1.metric("Best Bid", f"${metrics['Best Bid']:.2f}")
m2.metric("Best Ask", f"${metrics['Best Ask']:.2f}")
m3.metric("Spread", f"${metrics['Spread']:.4f}")
m4.metric("Mid Price", f"${metrics['Mid Price']:.4f}")

m5, m6, m7, m8 = st.columns(4)

m5.metric("Microprice", f"${metrics['Microprice']:.4f}")
m6.metric("Top Imbalance", f"{metrics['Top Imbalance']:.3f}")
m7.metric("Bid Depth", f"{metrics['Total Bid Depth']:,.0f}")
m8.metric("Ask Depth", f"{metrics['Total Ask Depth']:,.0f}")

current_signal = pressure_signal(
    metrics["Top Imbalance"],
    metrics["Total Imbalance"],
    metrics["Microprice"],
    metrics["Mid Price"]
)

if current_signal == "Buy Pressure":
    st.success(f"Signal: {current_signal}")
elif current_signal == "Sell Pressure":
    st.error(f"Signal: {current_signal}")
elif current_signal == "Balanced":
    st.info(f"Signal: {current_signal}")
else:
    st.warning(f"Signal: {current_signal}")

st.write(signal_message(current_signal))

st.divider()


# =============================
# Market impact
# =============================
section(
    "Market Order Impact",
    "Estimate how a market order consumes liquidity across price levels."
)

impact = estimate_market_impact(
    book=book,
    side=side,
    order_size=order_size
)

i1, i2, i3, i4 = st.columns(4)

i1.metric("Requested Size", f"{impact['Requested Size']:,.0f}")
i2.metric("Filled Size", f"{impact['Filled Size']:,.0f}")
i3.metric("Unfilled Size", f"{impact['Unfilled Size']:,.0f}")
i4.metric("Avg Fill Price", f"${impact['Average Fill Price']:.4f}")

st.metric("Levels Used", impact["Levels Used"])

if impact["Unfilled Size"] > 0:
    st.warning("The simulated market order is larger than visible book liquidity.")
else:
    st.success("The simulated market order was fully filled by visible liquidity.")

if side == "Buy":
    slippage = impact["Average Fill Price"] - metrics["Mid Price"]
else:
    slippage = metrics["Mid Price"] - impact["Average Fill Price"]

st.metric("Estimated Slippage vs Mid", f"${slippage:.4f}")

st.divider()


# =============================
# Depth chart
# =============================
section(
    "Liquidity Depth Chart",
    "Visualize bid and ask size available at each price level."
)

depth_df = pd.DataFrame({
    "Bid Price": book["Bid Price"],
    "Bid Size": book["Bid Size"],
    "Ask Price": book["Ask Price"],
    "Ask Size": book["Ask Size"]
})

fig1 = go.Figure()
fig1.add_trace(go.Bar(x=depth_df["Bid Price"], y=depth_df["Bid Size"],
                      name="Bid Size", marker_color="#10b981", width=tick_size * 0.8))
fig1.add_trace(go.Bar(x=depth_df["Ask Price"], y=depth_df["Ask Size"],
                      name="Ask Size", marker_color="#ef4444", width=tick_size * 0.8))
fig1.add_vline(x=metrics["Mid Price"], line_dash="dash", line_color="#94a3b8",
               annotation_text="Mid Price", annotation_position="top right")
fig1.update_layout(title="Order Book Depth", xaxis_title="Price", yaxis_title="Size",
                   barmode="overlay", **plotly_config())
st.plotly_chart(fig1, use_container_width=True)

st.divider()


# =============================
# Cumulative depth
# =============================
section(
    "Cumulative Depth",
    "Shows how much liquidity is available as price moves away from the best bid/ask."
)

cum_bid = book["Bid Size"].cumsum()
cum_ask = book["Ask Size"].cumsum()

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=list(range(len(cum_bid))), y=cum_bid.values,
                          mode="lines", name="Bid Cumulative Depth",
                          line=dict(color="#10b981", width=2)))
fig2.add_trace(go.Scatter(x=list(range(len(cum_ask))), y=cum_ask.values,
                          mode="lines", name="Ask Cumulative Depth",
                          line=dict(color="#ef4444", width=2)))
fig2.update_layout(title="Cumulative Depth", xaxis_title="Level", yaxis_title="Cumulative Size",
                   **plotly_config())
st.plotly_chart(fig2, use_container_width=True)

st.divider()


# =============================
# Microprice explanation
# =============================
section(
    "Microprice Explanation",
    "Microprice uses top-of-book liquidity to estimate short-term fair value."
)

st.write(
    "If bid size is much larger than ask size, the microprice moves closer to the ask, suggesting buy pressure."
)

st.write(
    "If ask size is much larger than bid size, the microprice moves closer to the bid, suggesting sell pressure."
)

explanation_df = pd.DataFrame({
    "Metric": [
        "Bid-Ask Spread",
        "Mid Price",
        "Microprice",
        "Top Imbalance",
        "Total Imbalance",
        "Slippage"
    ],
    "Meaning": [
        "Cost of immediately crossing the spread.",
        "Average of best bid and best ask.",
        "Liquidity-weighted short-term fair price.",
        "Liquidity imbalance at the best bid/ask.",
        "Liquidity imbalance across visible book levels.",
        "Execution cost compared with the mid price."
    ]
})

st.dataframe(explanation_df, use_container_width=True)

st.divider()


# =============================
# Save state
# =============================
st.session_state["order_book_signal"] = current_signal
st.session_state["order_book_spread"] = float(metrics["Spread"])
st.session_state["order_book_microprice"] = float(metrics["Microprice"])
st.session_state["order_book_top_imbalance"] = float(metrics["Top Imbalance"])
st.session_state["order_book_total_imbalance"] = float(metrics["Total Imbalance"])
st.session_state["order_book_slippage"] = float(slippage)


# =============================
# Next step
# =============================
next_step(
    "Use Execution, Trading Sim, or Risk Engine next to study how liquidity and slippage affect real strategy performance."
)