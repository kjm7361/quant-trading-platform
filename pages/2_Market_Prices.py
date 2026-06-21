import streamlit as st
import pandas as pd

from components.layout import setup_page, section, next_step

from data.universe import get_universe
from market.prices import fetch_latest_prices


# =============================
# Page setup
# =============================
setup_page(
    "US Market Prices Dashboard",
    "Track major US market universes, top gainers, top losers, and individual ticker prices.",
    "🗽"
)

# Optional: clear cached data when user clicks refresh
# Do not clear cache on every page load because it slows the app down.


# =============================
# Controls
# =============================
st.sidebar.header("Market Universe")

universe_name = st.sidebar.selectbox(
    "Universe",
    ["S&P 500", "Nasdaq 100", "Dow 30"],
    index=0
)

max_tickers = st.sidebar.slider(
    "Max tickers to load",
    min_value=10,
    max_value=200,
    value=100,
    step=10
)

st.sidebar.header("Quick Ticker Lookup")
single_ticker = st.sidebar.text_input("Enter a ticker", value="", placeholder="Example: AAPL")

refresh = st.sidebar.button("Refresh Prices")

if refresh:
    st.cache_data.clear()
    st.success("Cache cleared. Prices refreshed.")


# =============================
# Universe table
# =============================
section(
    f"{universe_name} Prices",
    "Prices come from Yahoo Finance. Percent change is based on last close versus previous close."
)

tickers = get_universe(universe_name)
tickers = tickers[:max_tickers]

st.caption(f"Showing {len(tickers)} tickers.")

prices_df = fetch_latest_prices(tickers, period="5d", interval="1d")

if prices_df is None or len(prices_df) == 0:
    st.warning("No price data returned. Try refreshing or reducing the number of tickers.")
else:
    show_df = prices_df.copy()

    show_df["price"] = show_df["price"].astype(float)
    show_df["prev_price"] = show_df["prev_price"].astype(float)
    show_df["pct_change"] = show_df["pct_change"].astype(float)

    if "ticker" in show_df.columns:
        show_df = show_df.sort_values("pct_change", ascending=False).reset_index(drop=True)

    # =============================
    # Market summary metrics
    # =============================
    gainers_count = int((show_df["pct_change"] > 0).sum())
    losers_count = int((show_df["pct_change"] < 0).sum())
    avg_change = float(show_df["pct_change"].mean())
    best_row = show_df.iloc[0]
    worst_row = show_df.sort_values("pct_change").iloc[0]

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Tickers Loaded", f"{len(show_df)}")
    m2.metric("Advancers", f"{gainers_count}")
    m3.metric("Decliners", f"{losers_count}")
    m4.metric("Average Change", f"{avg_change:+.2f}%")
    m5.metric("Best Ticker", str(best_row["ticker"]) if "ticker" in show_df.columns else "N/A")

    st.divider()

    # =============================
    # Top gainers and losers
    # =============================
    col1, col2 = st.columns(2)

    with col1:
        section("Top Gainers", "Strongest positive movers in the selected universe.")
        st.dataframe(
            show_df.head(10).style.format({
                "price": "{:.2f}",
                "prev_price": "{:.2f}",
                "pct_change": "{:+.2f}%"
            }),
            use_container_width=True
        )

    with col2:
        section("Top Losers", "Weakest negative movers in the selected universe.")
        losers_df = show_df.sort_values("pct_change").head(10)

        st.dataframe(
            losers_df.style.format({
                "price": "{:.2f}",
                "prev_price": "{:.2f}",
                "pct_change": "{:+.2f}%"
            }),
            use_container_width=True
        )

    st.divider()

    # =============================
    # Full table
    # =============================
    section("Full Market Table", "Complete price table for the selected universe.")

    st.dataframe(
        show_df.style.format({
            "price": "{:.2f}",
            "prev_price": "{:.2f}",
            "pct_change": "{:+.2f}%"
        }),
        use_container_width=True,
        height=520
    )

    # =============================
    # Quick insight
    # =============================
    section("Market Breadth Insight")

    if gainers_count > losers_count:
        st.success("More stocks are advancing than declining. Market breadth is positive for this universe.")
    elif losers_count > gainers_count:
        st.warning("More stocks are declining than advancing. Market breadth is weak for this universe.")
    else:
        st.info("Advancers and decliners are balanced. Market breadth is neutral.")


# =============================
# Single ticker lookup
# =============================
if single_ticker.strip() != "":
    st.divider()

    section("Single Ticker Lookup", "Quick lookup independent of the selected universe.")

    t = single_ticker.strip().upper()
    one = fetch_latest_prices([t], period="5d", interval="1d")

    if one is None or len(one) == 0:
        st.error(f"Could not load data for {t}. Check ticker spelling.")
    else:
        st.dataframe(
            one.style.format({
                "price": "{:.2f}",
                "prev_price": "{:.2f}",
                "pct_change": "{:+.2f}%"
            }),
            use_container_width=True
        )


# =============================
# Next step
# =============================
next_step("Use Market Anomalies or Daily Picks next to turn price movement into possible trading ideas.")