import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from components.layout import setup_page, section, next_step

from execution.sim_broker import init_db
from execution.sim_performance import load_trades_df, equity_curve_from_trades


# =============================
# Page setup
# =============================
setup_page(
    "Performance Dashboard",
    "Analyze simulated trading performance, equity curve, drawdown, positions, and realized PnL.",
    "📊"
)


# =============================
# Initialize database
# =============================
init_db()


# =============================
# Load trades
# =============================
section("Trade Data", "Load simulated trade history from the paper trading system.")

df_trades = load_trades_df()

if df_trades is None or len(df_trades) == 0:
    st.info("No trades found yet. Place some simulated trades first.")
    st.stop()

st.success(f"Loaded {len(df_trades)} simulated trades.")

st.divider()


# =============================
# Price map helper
# =============================
def get_price_map(symbols):
    price_map = {}

    try:
        from market import prices

        i = 0
        while i < len(symbols):
            s = symbols[i]

            if hasattr(prices, "get_latest_price"):
                price_map[s] = float(prices.get_latest_price(s))

            i += 1

    except:
        pass

    return price_map


# =============================
# Build performance data
# =============================
symbols = sorted(list(set([str(x).upper() for x in df_trades["symbol"].tolist()])))

price_map = get_price_map(symbols)

if len(price_map) == 0:
    price_map = None

equity_df, stats, blotter, pos_df = equity_curve_from_trades(
    df_trades,
    price_map=price_map
)


# Save to global session state for other pages
if equity_df is not None and len(equity_df) > 0:
    equity_series = pd.Series(
        equity_df["equity"].values,
        index=pd.to_datetime(equity_df["date"])
    )

    returns_series = equity_series.pct_change().dropna()

    st.session_state["equity_curve"] = equity_series
    st.session_state["strategy_returns"] = returns_series
    st.session_state["initial_capital"] = float(stats["starting_cash"])


# =============================
# KPIs
# =============================
section("Performance Summary", "Core simulated trading performance metrics.")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Starting Equity", f'${stats["starting_cash"]:,.2f}')
c2.metric("Ending Equity", f'${stats["ending_equity"]:,.2f}')
c3.metric("Total Return", f'{stats["total_return"]*100:.2f}%')
c4.metric("Max Drawdown", f'{stats["max_drawdown"]*100:.2f}%')

c5, c6, c7, c8 = st.columns(4)

c5.metric("Sharpe Daily", f'{stats["sharpe_daily"]:.2f}')
c6.metric("Win Rate", f'{stats["win_rate"]*100:.1f}%')
c7.metric("Profit Factor", f'{stats["profit_factor"]:.2f}')
c8.metric("Trades", str(stats["num_trades"]))

st.divider()


# =============================
# Performance insight
# =============================
section("Performance Insight")

if stats["total_return"] > 0 and stats["sharpe_daily"] > 1:
    st.success("The simulated strategy is profitable with strong risk-adjusted performance.")

elif stats["total_return"] > 0:
    st.info("The simulated strategy is profitable, but risk-adjusted performance should be reviewed.")

elif stats["max_drawdown"] < -0.10:
    st.warning("The strategy is currently negative and has meaningful drawdown risk.")

else:
    st.warning("The strategy is not currently profitable. Review trade selection, sizing, and execution.")

st.divider()


# =============================
# Equity curve plot
# =============================
section("Equity Curve", "Simulated account equity over time.")

fig = plt.figure(figsize=(10, 5))

plt.plot(
    pd.to_datetime(equity_df["date"]),
    equity_df["equity"]
)

plt.xlabel("Date")
plt.ylabel("Equity")
plt.title("Simulated Equity Curve")

st.pyplot(fig)

st.divider()


# =============================
# Drawdown
# =============================
section("Drawdown", "Peak-to-trough decline in simulated account value.")

peak = equity_df["equity"].cummax()
dd = (equity_df["equity"] / peak) - 1.0

dd_df = pd.DataFrame({
    "date": equity_df["date"],
    "drawdown": dd
})

fig2 = plt.figure(figsize=(10, 5))

plt.plot(
    pd.to_datetime(dd_df["date"]),
    dd_df["drawdown"]
)

plt.xlabel("Date")
plt.ylabel("Drawdown")
plt.title("Drawdown Curve")

st.pyplot(fig2)

st.divider()


# =============================
# Positions
# =============================
section("Open Positions", "Current simulated positions marked using available prices.")

if pos_df is None or len(pos_df) == 0:
    st.info("No open positions.")

else:
    st.dataframe(
        pos_df,
        use_container_width=True
    )

st.divider()


# =============================
# Trade blotter
# =============================
section("Trade Blotter", "Executed trades and realized PnL on sells.")

show = blotter.copy()

show["dt"] = show["dt"].astype(str)

st.dataframe(
    show[
        [
            "dt",
            "symbol",
            "side",
            "qty",
            "price",
            "realized_pl",
            "cash_after"
        ]
    ],
    use_container_width=True
)


# =============================
# Next step
# =============================
next_step(
    "Open Risk Engine, Monte Carlo, or Strategy DNA next to analyze this performance more deeply."
)