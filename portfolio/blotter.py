import pandas as pd


def holdings_snapshot(positions: pd.DataFrame, asof=None, top_n: int = 10):
    """
    Returns two DataFrames: top longs and top shorts for a given date.
    positions: index=date, columns=tickers, values=weights
    asof: date-like or None (uses last available date)
    """
    if positions is None or positions.empty:
        return pd.DataFrame(), pd.DataFrame()

    if asof is None:
        row = positions.iloc[-1]
        asof = positions.index[-1]
    else:
        # pick last date <= asof
        idx = positions.index[positions.index <= pd.to_datetime(asof)]
        if len(idx) == 0:
            row = positions.iloc[0]
            asof = positions.index[0]
        else:
            row = positions.loc[idx[-1]]
            asof = idx[-1]

    row = row.fillna(0.0)
    longs = row[row > 0].sort_values(ascending=False).head(top_n)
    shorts = row[row < 0].sort_values(ascending=True).head(top_n)  # most negative first

    long_df = pd.DataFrame({
        "Ticker": longs.index,
        "Weight": longs.values
    })
    short_df = pd.DataFrame({
        "Ticker": shorts.index,
        "Weight": shorts.values
    })

    long_df["As Of"] = str(pd.to_datetime(asof).date())
    short_df["As Of"] = str(pd.to_datetime(asof).date())

    return long_df.reset_index(drop=True), short_df.reset_index(drop=True)


def trade_blotter(positions: pd.DataFrame, rebalance_dates, threshold: float = 0.001):
    """
    Build a trade blotter by differencing positions on rebalance dates.
    rebalance_dates: iterable of dates (must align to positions.index)
    threshold: ignore tiny trades (absolute delta below threshold)
    Returns a DataFrame: Date, Ticker, PrevWeight, NewWeight, Trade (delta)
    """
    if positions is None or positions.empty:
        return pd.DataFrame(columns=["Date", "Ticker", "PrevWeight", "NewWeight", "Trade"])

    if rebalance_dates is None or len(rebalance_dates) == 0:
        return pd.DataFrame(columns=["Date", "Ticker", "PrevWeight", "NewWeight", "Trade"])

    # Keep only rebalance dates that exist in positions index
    reb = pd.to_datetime(pd.Index(rebalance_dates))
    reb = reb.intersection(pd.to_datetime(positions.index))
    reb = reb.sort_values()

    if len(reb) == 0:
        return pd.DataFrame(columns=["Date", "Ticker", "PrevWeight", "NewWeight", "Trade"])

    rows = []
    prev_pos = None

    for d in reb:
        pos = positions.loc[d].fillna(0.0)

        if prev_pos is None:
            # First rebalance: treat previous as 0
            prev_pos = pos * 0.0

        delta = (pos - prev_pos).fillna(0.0)

        # Filter small changes
        delta = delta[delta.abs() >= threshold]

        if not delta.empty:
            for ticker, trade in delta.items():
                rows.append({
                    "Date": str(pd.to_datetime(d).date()),
                    "Ticker": ticker,
                    "PrevWeight": float(prev_pos.get(ticker, 0.0)),
                    "NewWeight": float(pos.get(ticker, 0.0)),
                    "Trade": float(trade),
                })

        prev_pos = pos

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["Date", "Ticker", "PrevWeight", "NewWeight", "Trade"])

    # Helpful sort: by date then biggest absolute trades first
    df["AbsTrade"] = df["Trade"].abs()
    df = df.sort_values(["Date", "AbsTrade"], ascending=[False, False]).drop(columns=["AbsTrade"]).reset_index(drop=True)
    return df
