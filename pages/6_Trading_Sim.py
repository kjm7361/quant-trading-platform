import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np
import yfinance as yf

from components.layout import setup_page, section, next_step

from execution.sim_broker import (
    init_db,
    get_cash,
    get_positions,
    place_market_order,
    list_trades,
    reset_account
)

# =============================
# Page setup
# =============================
setup_page(
    "Simulated Paper Trading",
    "Place simulated trades, monitor positions, and build portfolio history for analytics and risk systems.",
    "💹"
)


# =============================
# Price loader
# =============================
def get_live_price(symbol):
    symbol = str(symbol).upper().strip()

    try:
        from market import prices

        if hasattr(prices, "get_latest_price"):
            return float(prices.get_latest_price(symbol))

        if hasattr(prices, "get_price"):
            return float(prices.get_price(symbol))

        if hasattr(prices, "get_last_price"):
            return float(prices.get_last_price(symbol))

    except:
        pass

    return None


# =============================
# Historical price loader
# =============================
def load_price_history(symbols, period="1mo", interval="1d"):
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
                close_df[clean_symbols[0]] = pd.to_numeric(data["Close"], errors="coerce")
            else:
                return pd.DataFrame()

        close_df = close_df.sort_index()
        close_df = close_df.ffill().dropna(how="all")

        return close_df

    except:
        return pd.DataFrame()


# =============================
# Equity curve builder
# =============================
def build_equity_curve_from_trades_mark_to_market(
    trades,
    starting_cash=100000.0,
    period="1mo",
    interval="1d"
):
    if len(trades) == 0:
        return pd.Series(dtype=float)

    trade_rows = []
    symbols = []

    i = 0
    while i < len(trades):
        t = trades[i]

        sym = str(t["symbol"]).upper().strip()
        side = str(t["side"]).lower().strip()
        qty = float(t["qty"])
        price = float(t["price"])
        ts = pd.to_datetime(t["ts"], unit="s")

        trade_rows.append({
            "time": ts,
            "symbol": sym,
            "side": side,
            "qty": qty,
            "price": price
        })

        if sym not in symbols:
            symbols.append(sym)

        i += 1

    trades_df = pd.DataFrame(trade_rows)
    trades_df = trades_df.sort_values("time").reset_index(drop=True)

    price_df = load_price_history(symbols, period=period, interval=interval)

    if price_df.empty:
        return pd.Series(dtype=float)

    j = 0
    while j < len(symbols):
        sym = symbols[j]

        if sym not in price_df.columns:
            price_df[sym] = np.nan

        j += 1

    price_df = price_df.sort_index().ffill().dropna(how="all")

    holdings = {}
    cash = float(starting_cash)

    k = 0
    while k < len(symbols):
        holdings[symbols[k]] = 0.0
        k += 1

    equity_values = []
    trade_ptr = 0
    n_trades = len(trades_df)

    time_index = list(price_df.index)

    m = 0
    while m < len(time_index):
        current_time = time_index[m]

        while trade_ptr < n_trades and trades_df.loc[trade_ptr, "time"] <= current_time:
            tr_row = trades_df.loc[trade_ptr]

            sym = tr_row["symbol"]
            side = tr_row["side"]
            qty = float(tr_row["qty"])
            px = float(tr_row["price"])

            if side == "buy":
                cash -= qty * px
                holdings[sym] += qty

            elif side == "sell":
                cash += qty * px
                holdings[sym] -= qty

            trade_ptr += 1

        equity_now = cash

        s_idx = 0
        while s_idx < len(symbols):
            sym = symbols[s_idx]
            mark_px = price_df.loc[current_time, sym]

            if pd.notna(mark_px):
                equity_now += holdings[sym] * float(mark_px)

            s_idx += 1

        equity_values.append(equity_now)

        m += 1

    equity_curve = pd.Series(equity_values, index=price_df.index)
    equity_curve = equity_curve.dropna()

    return equity_curve


# =============================
# Initialize DB
# =============================
init_db()

# =============================
# Kill switch protection
# =============================
if st.session_state.get("kill_switch", False):
    st.error("Trading Disabled Due to Risk Limits")

    reasons = st.session_state.get("kill_switch_reasons", [])

    k = 0
    while k < len(reasons):
        st.write(f"- {reasons[k]}")
        k += 1

    st.stop()


# =============================
# Sidebar
# =============================
with st.sidebar:
    st.subheader("Sim Account")

    current_cash = float(get_cash())

    st.metric("Cash", f"${current_cash:,.2f}")

    if st.button("Reset Account to 100k"):
        reset_account(100000.0)

        st.session_state["strategy_returns"] = pd.Series(dtype=float)
        st.session_state["equity_curve"] = pd.Series(dtype=float)
        st.session_state["initial_capital"] = 100000.0

        st.success("Account reset complete.")


# =============================
# Order ticket
# =============================
section("Order Ticket", "Place simulated buy and sell orders.")

c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1.2])

symbol = c1.text_input("Symbol", value="AAPL")
side = c2.selectbox("Side", ["buy", "sell"])
qty = c3.number_input("Quantity", min_value=0.0, value=1.0, step=1.0)

auto_price = get_live_price(symbol)

if auto_price is None:
    price = c4.number_input(
        "Fill Price",
        min_value=0.0,
        value=100.0,
        step=0.01
    )

    st.caption("Connect your market price module later for automatic pricing.")

else:
    price = auto_price
    c4.metric("Live Price", round(price, 4))

if st.button("Place Market Order", type="primary"):
    res = place_market_order(symbol, qty, side, price)

    if res.get("ok"):
        st.success("Order filled successfully.")
        st.write(res)

    else:
        st.error(res.get("error", "Order failed"))

st.divider()

# =============================
# Positions
# =============================
section("Current Positions", "Open positions and unrealized profit/loss.")

pos = get_positions()

positions_rows = []
total_market_value = 0.0
total_unrealized_pl = 0.0

if len(pos) == 0:
    st.info("No open positions.")

else:
    i = 0

    while i < len(pos):
        p = pos[i]

        live = get_live_price(p["symbol"])

        if live is None:
            live = p["avg_price"]

        mv = float(p["qty"]) * float(live)
        upl = (float(live) - float(p["avg_price"])) * float(p["qty"])

        total_market_value += mv
        total_unrealized_pl += upl

        positions_rows.append({
            "symbol": p["symbol"],
            "qty": float(p["qty"]),
            "avg_price": float(p["avg_price"]),
            "mark_price": float(live),
            "market_value": mv,
            "unrealized_pl": upl
        })

        i += 1

    positions_df = pd.DataFrame(positions_rows)

    st.dataframe(
        positions_df,
        use_container_width=True
    )

st.divider()

# =============================
# Trade history
# =============================
section("Trade History", "Recent executed simulated trades.")

tr = list_trades(limit=100)

trade_rows = []

if len(tr) == 0:
    st.info("No trades yet.")

else:
    j = 0

    while j < len(tr):
        t = tr[j]

        trade_rows.append({
            "time": datetime.fromtimestamp(t["ts"]).strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": t["symbol"],
            "side": t["side"],
            "qty": t["qty"],
            "price": t["price"]
        })

        j += 1

    st.dataframe(
        pd.DataFrame(trade_rows),
        use_container_width=True
    )

st.divider()

# =============================
# Portfolio snapshot
# =============================
section("Portfolio Snapshot", "Current simulated portfolio state.")

initial_capital = 100000.0

portfolio_equity_now = current_cash + total_market_value
portfolio_return_now = (portfolio_equity_now / initial_capital) - 1

m1, m2, m3, m4 = st.columns(4)

m1.metric("Current Cash", f"${current_cash:,.2f}")
m2.metric("Market Value", f"${total_market_value:,.2f}")
m3.metric("Portfolio Equity", f"${portfolio_equity_now:,.2f}")
m4.metric("Total Return", f"{portfolio_return_now*100:.2f}%")

# =============================
# Build equity curve
# =============================
equity_curve = build_equity_curve_from_trades_mark_to_market(
    tr,
    starting_cash=initial_capital,
    period="1mo",
    interval="1d"
)

if len(equity_curve) >= 2:
    strategy_returns = equity_curve.pct_change().dropna()

else:
    strategy_returns = pd.Series(dtype=float)

# Save globally
st.session_state["strategy_returns"] = strategy_returns
st.session_state["equity_curve"] = equity_curve
st.session_state["initial_capital"] = initial_capital

# =============================
# Equity curve
# =============================
if len(equity_curve) > 0:
    section(
        "Equity Curve",
        "Portfolio value marked to market using historical prices."
    )

    st.line_chart(equity_curve)

    used_symbols = []

    i = 0
    while i < len(tr):
        sym = str(tr[i]["symbol"]).upper().strip()

        if sym not in used_symbols:
            used_symbols.append(sym)

        i += 1

    st.caption(
        "Marked to market using historical prices for: "
        + ", ".join(used_symbols)
    )

# =============================
# Performance insight
# =============================
section("Trading Insight")

if portfolio_return_now > 0.10:
    st.success("The simulated portfolio is performing strongly relative to starting capital.")

elif portfolio_return_now > 0:
    st.info("The simulated portfolio is profitable but still within moderate return range.")

else:
    st.warning("The simulated portfolio is currently below starting capital.")

st.success("Trading simulation data saved for Risk Engine, Dashboard, Monte Carlo, Alerts, and Strategy DNA.")

# =============================
# Next step
# =============================
next_step(
    "Open Risk Engine or Portfolio Optimizer next to evaluate risk, allocation, and portfolio quality."
)