import pandas as pd


def _safe_read_html(url):
    """
    Helper to read a table from Wikipedia. If it fails (network / packages),
    we return None and fall back to a small built-in list.
    """
    try:
        tables = pd.read_html(url)
        return tables
    except Exception:
        return None


def get_sp500_tickers():
    """
    Returns a list of S&P 500 tickers (best-effort).
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = _safe_read_html(url)

    if tables is not None and len(tables) > 0:
        df = tables[0]
        tickers = df["Symbol"].astype(str).tolist()
        # Yahoo uses '-' instead of '.' (BRK.B -> BRK-B)
        tickers = [t.replace(".", "-").strip().upper() for t in tickers]
        return tickers

    # Fallback (small)
    return ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "JPM", "V", "UNH"]


def get_nasdaq100_tickers():
    """
    Returns a list of Nasdaq-100 tickers (best-effort).
    """
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    tables = _safe_read_html(url)

    if tables is not None:
        # Wikipedia page structure can vary; we search for a table with a 'Ticker' column
        for df in tables:
            cols = [c.lower() for c in df.columns.astype(str)]
            if "ticker" in cols:
                col = df.columns[cols.index("ticker")]
                tickers = df[col].astype(str).tolist()
                tickers = [t.replace(".", "-").strip().upper() for t in tickers]
                # Remove weird entries
                tickers = [t for t in tickers if t != "" and t != "nan"]
                return tickers

    # Fallback (small)
    return ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "AVGO", "COST", "PEP", "ADBE"]


def get_dow30_tickers():
    """
    Returns a list of Dow 30 tickers (best-effort).
    """
    url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
    tables = _safe_read_html(url)

    if tables is not None:
        for df in tables:
            cols = [c.lower() for c in df.columns.astype(str)]
            # Many pages have 'Symbol' or 'Ticker'
            if "symbol" in cols:
                col = df.columns[cols.index("symbol")]
                tickers = df[col].astype(str).tolist()
                tickers = [t.replace(".", "-").strip().upper() for t in tickers]
                tickers = [t for t in tickers if t != "" and t != "nan"]
                # Dow table sometimes includes extra rows; keep unique
                return list(dict.fromkeys(tickers))
            if "ticker" in cols:
                col = df.columns[cols.index("ticker")]
                tickers = df[col].astype(str).tolist()
                tickers = [t.replace(".", "-").strip().upper() for t in tickers]
                tickers = [t for t in tickers if t != "" and t != "nan"]
                return list(dict.fromkeys(tickers))

    # Fallback (small)
    return ["AAPL", "MSFT", "JNJ", "JPM", "V", "PG", "KO", "DIS", "MCD", "BA"]


def get_universe(name):
    """
    name: 'S&P 500' or 'Nasdaq 100' or 'Dow 30'
    """
    if name == "S&P 500":
        return get_sp500_tickers()
    if name == "Nasdaq 100":
        return get_nasdaq100_tickers()
    if name == "Dow 30":
        return get_dow30_tickers()
    return get_sp500_tickers()
