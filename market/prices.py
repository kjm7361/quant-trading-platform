import pandas as pd
import yfinance as yf


def _extract_close(raw, tickers):
    """
    Robustly extract a close-price DataFrame (date x ticker) from yfinance output.
    Handles MultiIndex column orders: (Field, Ticker) or (Ticker, Field).
    """
    if raw is None or len(raw) == 0:
        return pd.DataFrame()

    cols = raw.columns

    # Case 1: MultiIndex columns
    if isinstance(cols, pd.MultiIndex):
        level0 = [str(x) for x in cols.get_level_values(0)]
        level1 = [str(x) for x in cols.get_level_values(1)]

        # (Field, Ticker) -> level 0 contains "Close"
        if "Close" in set(level0):
            close = raw.xs("Close", axis=1, level=0, drop_level=True)
            return close

        # (Ticker, Field) -> level 1 contains "Close"
        if "Close" in set(level1):
            close = raw.xs("Close", axis=1, level=1, drop_level=True)
            return close

        # Fallback: try Adj Close
        if "Adj Close" in set(level0):
            close = raw.xs("Adj Close", axis=1, level=0, drop_level=True)
            return close
        if "Adj Close" in set(level1):
            close = raw.xs("Adj Close", axis=1, level=1, drop_level=True)
            return close

        return pd.DataFrame()

    # Case 2: Single-index columns
    if "Close" in raw.columns:
        close = raw["Close"]
        if isinstance(close, pd.Series):
            close = close.to_frame()
            close.columns = tickers[:1]
        return close

    if "Adj Close" in raw.columns:
        close = raw["Adj Close"]
        if isinstance(close, pd.Series):
            close = close.to_frame()
            close.columns = tickers[:1]
        return close

    return pd.DataFrame()


def fetch_latest_prices(tickers, period="5d", interval="1d"):
    tickers = [str(t).strip().upper() for t in tickers if str(t).strip() != ""]
    tickers = list(dict.fromkeys(tickers))

    if len(tickers) == 0:
        return pd.DataFrame(columns=["price", "prev_price", "pct_change"])

    raw = yf.download(
        tickers=tickers,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False
    )

    close = _extract_close(raw, tickers)

    close = close.dropna(how="all")
    if close.shape[0] == 0:
        return pd.DataFrame(columns=["price", "prev_price", "pct_change"])

    # Ensure columns are tickers (sometimes yfinance gives non-string)
    close.columns = [str(c).strip().upper() for c in close.columns]

    last = close.iloc[-1]
    prev = close.iloc[-2] if close.shape[0] >= 2 else close.iloc[-1]

    out = pd.DataFrame({
        "price": last,
        "prev_price": prev
    })

    out["pct_change"] = (out["price"] / out["prev_price"] - 1.0) * 100.0
    out.index.name = "ticker"

    out = out.dropna()
    out = out.sort_values("pct_change", ascending=False)

    return out


def get_live_price(symbol: str):
    """Return the most recent trade price for a single ticker, or None on failure."""
    symbol = str(symbol).strip().upper()
    try:
        t = yf.Ticker(symbol)
        price = t.fast_info.last_price
        if price is not None and price == price:   # nan guard
            return float(price)
    except Exception:
        pass
    try:
        df = fetch_latest_prices([symbol], period="2d", interval="1d")
        if not df.empty:
            return float(df["price"].iloc[0])
    except Exception:
        pass
    return None


# Back-compat alias: Trading Sim probes for this via hasattr(prices, "get_latest_price")
get_latest_price = get_live_price
