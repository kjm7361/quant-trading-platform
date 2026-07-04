import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

from components.layout import setup_page, section, next_step, plotly_config

from recommendations.daily_pick import compute_daily_scores


# =============================
# Page setup
# =============================
setup_page(
    "Daily USA Stock Picks",
    "Rank US stocks using transparent price-based signals such as momentum, stability, volatility, and drawdown.",
    "📌"
)

st.info("Educational only — not financial advice.")


# -----------------------------
# Inputs
# -----------------------------
st.sidebar.header("Daily Picks Settings")

default_watchlist = "AAPL,MSFT,NVDA,AMZN,GOOG,META,TSLA,AVGO,COST,LLY,JPM,V,MA,UNH,XOM,HD,PG"

tickers_text = st.sidebar.text_area(
    "USA Watchlist Tickers",
    value=default_watchlist,
    height=110
)

period = st.sidebar.selectbox("Lookback Window", ["1y", "2y", "5y"], index=1)
top_n = st.sidebar.slider("Show Top N Picks", 3, 20, 10, step=1)

manual_refresh = st.sidebar.button("Refresh Now")

tickers = [t.strip().upper() for t in tickers_text.split(",") if t.strip()]

if len(tickers) < 3:
    st.warning("Please enter at least 3 tickers.")
    st.stop()


# -----------------------------
# Data download cached
# -----------------------------
@st.cache_data(ttl=60 * 60 * 6)
def download_close_prices(tickers_list, period_str):
    raw = yf.download(
        tickers_list,
        period=period_str,
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="column",
    )

    if raw is None or raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw.columns.get_level_values(0):
            close = raw["Close"].copy()
        elif "Adj Close" in raw.columns.get_level_values(0):
            close = raw["Adj Close"].copy()
        else:
            close = pd.DataFrame()

    else:
        if "Close" in raw.columns:
            close = raw["Close"].to_frame()
        elif "Adj Close" in raw.columns:
            close = raw["Adj Close"].to_frame()
        else:
            close = pd.DataFrame()

    close = close.dropna(how="all")
    return close


if manual_refresh:
    download_close_prices.clear()
    st.success("Price cache cleared. Data refreshed.")

close_prices = download_close_prices(tickers, period)

if close_prices is None or close_prices.empty:
    st.error("Could not fetch prices. Try fewer tickers or refresh.")
    st.stop()


# -----------------------------
# Score and rank
# -----------------------------
section("Top Picks Today", "Ranked by price-based momentum and risk/stability signals.")

scores_df, diag_df = compute_daily_scores(close_prices)

top = scores_df.head(top_n).copy()
top = top.join(diag_df, how="left")

top = top.reset_index().rename(columns={"index": "Ticker"})
top["score"] = top["score"].astype(float)

best_ticker = str(top.iloc[0]["Ticker"]) if len(top) > 0 else "N/A"
best_score = float(top.iloc[0]["score"]) if len(top) > 0 else 0.0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Tickers Scanned", f"{len(tickers)}")
m2.metric("Top Picks Shown", f"{top_n}")
m3.metric("Best Ticker", best_ticker)
m4.metric("Best Score", f"{best_score:.3f}")

st.dataframe(
    top.style.format({
        "score": "{:.3f}",
        "mom_3m": "{:.2%}",
        "mom_12m": "{:.2%}",
        "vol_3m": "{:.2%}",
        "worst_dd_6m": "{:.2%}",
    }),
    use_container_width=True
)

st.caption("Higher momentum is better, lower volatility is better, and smaller drawdowns are better.")

st.divider()


# -----------------------------
# Insight
# -----------------------------
section("Signal Insight", "Quick interpretation of the top-ranked stock.")

if len(top) > 0:
    row = top.iloc[0]

    msg_parts = []

    if "mom_3m" in row and pd.notna(row["mom_3m"]):
        msg_parts.append(f"3-month momentum: {row['mom_3m']:.2%}")

    if "mom_12m" in row and pd.notna(row["mom_12m"]):
        msg_parts.append(f"12-month momentum: {row['mom_12m']:.2%}")

    if "vol_3m" in row and pd.notna(row["vol_3m"]):
        msg_parts.append(f"3-month volatility: {row['vol_3m']:.2%}")

    if "worst_dd_6m" in row and pd.notna(row["worst_dd_6m"]):
        msg_parts.append(f"worst 6-month drawdown: {row['worst_dd_6m']:.2%}")

    st.success(f"{best_ticker} is the highest-ranked pick based on the current scoring model.")

    if len(msg_parts) > 0:
        st.write(" | ".join(msg_parts))

else:
    st.info("No ranked picks available.")

st.divider()


# -----------------------------
# Charts for top picks
# -----------------------------
section("Price Charts", "Historical close-price charts for the top-ranked picks.")

cols = st.columns(2)

i = 0
for row in top.itertuples(index=False):
    ticker = row.Ticker

    if ticker not in close_prices.columns:
        continue

    series = close_prices[ticker].dropna()

    with cols[i % 2]:
        fig = go.Figure(go.Scatter(x=series.index, y=series.values, mode="lines",
                                   line=dict(color="#10b981", width=2)))
        fig.update_layout(title=ticker, xaxis_title="Date", yaxis_title="Close Price",
                          **plotly_config())
        st.plotly_chart(fig, use_container_width=True)

    i += 1


# -----------------------------
# Export ranked list
# -----------------------------
section("Export", "Download the ranked stock-pick table as a CSV file.")

csv_bytes = top.to_csv(index=False).encode("utf-8")

st.download_button(
    "Download Today's Picks CSV",
    data=csv_bytes,
    file_name="daily_picks.csv",
    mime="text/csv",
)


# -----------------------------
# Next step
# -----------------------------
next_step("Use Trading Sim or Backtest next to test whether the selected picks translate into better portfolio performance.")