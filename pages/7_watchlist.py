import streamlit as st
import pandas as pd

from components.layout import setup_page, section, next_step

from watchlist.store import (
    get_watchlist,
    add_to_watchlist,
    remove_from_watchlist
)

from market.prices import fetch_latest_prices

from watchlist.alerts import (
    get_alerts,
    add_alert,
    remove_alert
)

from watchlist.notify import (
    get_history,
    add_notification,
    was_recently_triggered,
    clear_history
)


# =============================
# Page setup
# =============================
setup_page(
    "My Watchlist",
    "Track favorite stocks, monitor alerts, and manage notifications in one place.",
    "⭐"
)


# -----------------------------
# Require login
# -----------------------------
if "logged_in" not in st.session_state or not st.session_state.get("logged_in", False):
    st.warning("Please log in from the main app page first.")
    st.stop()

username = st.session_state.get("username", None)

if username is None:
    st.warning("No username found in session.")
    st.stop()


# =============================
# Notifications
# =============================
section(
    "Notifications",
    "Triggered alert history. Anti-spam prevents duplicate notifications within 120 minutes."
)

hist = get_history(username)

colA, colB = st.columns([1, 3])

with colA:
    if st.button("Clear Notifications"):
        clear_history(username)
        st.success("Notifications cleared.")
        st.rerun()

with colB:
    st.caption("Recent triggered alert activity.")

if len(hist) == 0:
    st.info("No notifications yet.")

else:
    notif_count = min(len(hist), 20)

    m1, m2 = st.columns(2)
    m1.metric("Total Notifications", f"{len(hist)}")
    m2.metric("Showing Latest", f"{notif_count}")

    st.divider()

    i = 0
    while i < notif_count:
        item = hist[i]

        ticker = item.get("ticker", "")
        message = item.get("message", "")
        time_utc = item.get("time_utc", "")

        st.info(f"{ticker} | {message} | {time_utc}")

        i += 1

st.divider()


# =============================
# Add ticker
# =============================
section(
    "Add a Ticker",
    "Add stocks to your personal watchlist."
)

c1, c2 = st.columns([3, 1])

with c1:
    new_ticker = st.text_input(
        "Ticker",
        value="",
        placeholder="AAPL, MSFT, TSLA ..."
    )

with c2:
    if st.button("Add Ticker"):
        if new_ticker.strip() == "":
            st.error("Enter a ticker.")
        else:
            add_to_watchlist(username, new_ticker)

            st.success(f"Added {new_ticker.strip().upper()}")

            st.rerun()

st.divider()


# =============================
# Watchlist
# =============================
section(
    "Watchlist Prices",
    "Live watchlist prices and daily percent changes."
)

tickers = get_watchlist(username)

if len(tickers) == 0:
    st.info("Your watchlist is empty. Add a ticker above.")
    st.stop()

prices_df = fetch_latest_prices(
    tickers,
    period="5d",
    interval="1d"
)

if prices_df is None or len(prices_df) == 0:
    st.warning("No price data returned. Try again.")
    st.stop()

prices_df = prices_df.copy()

prices_df["price"] = prices_df["price"].astype(float)
prices_df["prev_price"] = prices_df["prev_price"].astype(float)
prices_df["pct_change"] = prices_df["pct_change"].astype(float)

# =============================
# Market summary
# =============================
gainers = int((prices_df["pct_change"] > 0).sum())
losers = int((prices_df["pct_change"] < 0).sum())
avg_change = float(prices_df["pct_change"].mean())

best_idx = prices_df["pct_change"].idxmax()
worst_idx = prices_df["pct_change"].idxmin()

best_ticker = str(best_idx)
worst_ticker = str(worst_idx)

m1, m2, m3, m4, m5 = st.columns(5)

m1.metric("Watchlist Size", f"{len(tickers)}")
m2.metric("Advancers", f"{gainers}")
m3.metric("Decliners", f"{losers}")
m4.metric("Best Ticker", best_ticker)
m5.metric("Average Change", f"{avg_change:+.2f}%")

st.dataframe(
    prices_df.style.format({
        "price": "{:.2f}",
        "prev_price": "{:.2f}",
        "pct_change": "{:+.2f}%"
    }),
    use_container_width=True,
    height=420
)

st.divider()


# =============================
# Alerts
# =============================
section(
    "Alerts",
    "Create and monitor custom price or percent-change alerts."
)

alerts = get_alerts(username)

# Build lookup dictionaries
price_lookup = {}
pct_lookup = {}

if prices_df is not None and len(prices_df) > 0:
    for t in prices_df.index:
        try:
            price_lookup[str(t).upper()] = float(prices_df.loc[t, "price"])
            pct_lookup[str(t).upper()] = float(prices_df.loc[t, "pct_change"])
        except Exception:
            pass


# =============================
# Check triggers
# =============================
triggered = []

for i, a in enumerate(alerts):

    t = str(a.get("ticker", "")).upper()

    if t not in price_lookup:
        continue

    px = price_lookup[t]
    pct = pct_lookup.get(t, 0.0)

    above = a.get("above", None)
    below = a.get("below", None)
    pct_above = a.get("pct_above", None)

    hit = False
    reasons = []

    if above is not None and above != "" and px > float(above):
        hit = True
        reasons.append(f"Price {px:.2f} > {float(above):.2f}")

    if below is not None and below != "" and px < float(below):
        hit = True
        reasons.append(f"Price {px:.2f} < {float(below):.2f}")

    if pct_above is not None and pct_above != "" and pct > float(pct_above):
        hit = True
        reasons.append(f"% Change {pct:+.2f}% > {float(pct_above):+.2f}%")

    if hit:
        triggered.append((i, t, reasons))

        if not was_recently_triggered(username, i, within_minutes=120):

            add_notification(
                username=username,
                ticker=t,
                message=", ".join(reasons),
                alert_index=i
            )

# =============================
# Triggered alerts
# =============================
if len(triggered) > 0:
    st.error("Triggered Alerts")

    i = 0
    while i < len(triggered):
        _, t, reasons = triggered[i]

        st.write(f"**{t}** | " + ", ".join(reasons))

        i += 1

else:
    st.success("No alerts triggered right now.")

st.divider()


# =============================
# Create alert
# =============================
section(
    "Create Alert",
    "Create custom watchlist alert conditions."
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    alert_ticker = st.selectbox(
        "Ticker",
        options=tickers,
        index=0
    )

with c2:
    above = st.text_input(
        "Price Above",
        value=""
    )

with c3:
    below = st.text_input(
        "Price Below",
        value=""
    )

with c4:
    pct_above = st.text_input(
        "% Change Above",
        value=""
    )

if st.button("Save Alert"):

    a_above = float(above) if above.strip() != "" else None
    a_below = float(below) if below.strip() != "" else None
    a_pct = float(pct_above) if pct_above.strip() != "" else None

    add_alert(
        username,
        alert_ticker,
        above=a_above,
        below=a_below,
        pct_above=a_pct
    )

    st.success("Alert saved.")

    st.rerun()

st.divider()


# =============================
# Existing alerts
# =============================
section(
    "Your Alerts",
    "Manage existing watchlist alerts."
)

alerts = get_alerts(username)

if len(alerts) == 0:
    st.info("No alerts set.")

else:
    i = 0

    while i < len(alerts):
        a = alerts[i]

        t = a.get("ticker", "")

        st.write(
            f"**{i}. {t}** | "
            f"above={a.get('above')} | "
            f"below={a.get('below')} | "
            f"pct_above={a.get('pct_above')}"
        )

        if st.button(f"Delete Alert #{i}", key=f"del_alert_{i}"):

            remove_alert(username, i)

            st.success("Alert deleted.")

            st.rerun()

        i += 1

st.divider()


# =============================
# Remove tickers
# =============================
section(
    "Remove Tickers",
    "Remove selected stocks from the watchlist."
)

remove_choice = st.multiselect(
    "Select tickers to remove",
    options=tickers,
    default=[]
)

if st.button("Remove Selected"):

    for t in remove_choice:
        remove_from_watchlist(username, t)

    st.success("Removed selected tickers.")

    st.rerun()


# =============================
# Watchlist insight
# =============================
section("Watchlist Insight")

if gainers > losers:
    st.success("Most watchlist stocks are positive today.")

elif losers > gainers:
    st.warning("Most watchlist stocks are negative today.")

else:
    st.info("Watchlist performance is currently balanced.")


# =============================
# Next step
# =============================
next_step(
    "Use Daily Picks, Trading Sim, or Market News next to turn watchlist ideas into actionable trades."
)