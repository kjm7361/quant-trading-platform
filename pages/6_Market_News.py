import streamlit as st

from components.layout import setup_page, section, next_step

from news.rss import market_headlines, ticker_headlines


# =============================
# Page setup
# =============================
setup_page(
    "Real Market News",
    "View live market headlines and optional ticker-specific news from Google News RSS.",
    "📰"
)


# =============================
# Controls
# =============================
st.sidebar.header("News Controls")

refresh = st.sidebar.button("Refresh Headlines")
ticker = st.sidebar.text_input("Ticker news optional", value="", placeholder="Example: AAPL")

st.sidebar.caption("News source: Google News RSS headlines and links.")

if refresh:
    st.cache_data.clear()
    st.success("Headlines refreshed.")


# =============================
# Helper
# =============================
def render_news_items(items, max_items=25):
    if len(items) == 0:
        st.warning("No headlines returned right now.")
        return

    i = 0
    while i < min(len(items), max_items):
        it = items[i]

        title = it.get("title", "")
        link = it.get("link", "")
        source = it.get("source", "")
        published = it.get("published", "")

        meta = []
        if source:
            meta.append(source)
        if published:
            meta.append(published)

        with st.container():
            st.markdown(f"**{title}**")

            if len(meta) > 0:
                st.caption(" | ".join(meta))

            if link:
                st.markdown(f"[Open article]({link})")

            st.divider()

        i += 1


# =============================
# Market headlines
# =============================
section("US Market Headlines", "Broad market news, macro headlines, and financial market updates.")

try:
    items = market_headlines()

    c1, c2, c3 = st.columns(3)
    c1.metric("Headlines Loaded", f"{len(items)}")
    c2.metric("Source", "Google News RSS")
    c3.metric("Mode", "Market")

    st.divider()

    render_news_items(items, max_items=25)

except Exception as e:
    st.error("Could not load market headlines.")
    st.code(str(e))


# =============================
# Ticker headlines
# =============================
if ticker.strip() != "":
    st.divider()

    clean_ticker = ticker.strip().upper()

    section(f"{clean_ticker} Headlines", "Ticker-specific headlines for the selected symbol.")

    try:
        titems = ticker_headlines(clean_ticker)

        c1, c2, c3 = st.columns(3)
        c1.metric("Headlines Loaded", f"{len(titems)}")
        c2.metric("Ticker", clean_ticker)
        c3.metric("Source", "Google News RSS")

        st.divider()

        render_news_items(titems, max_items=25)

    except Exception as e:
        st.error("Could not load ticker headlines.")
        st.code(str(e))


# =============================
# Next step
# =============================
next_step("Use Market Prices, Daily Picks, or Strategy DNA next to connect news context with signals and portfolio behavior.")