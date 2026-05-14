import sqlite3
import pandas as pd
import math

from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = str(PROJECT_ROOT / "storage" / "sim_trading.db")


def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def load_trades_df():
    c = _conn()
    df = pd.read_sql_query(
        "SELECT ts, symbol, side, qty, price FROM trades ORDER BY ts ASC",
        c
    )
    c.close()
    if len(df) == 0:
        return df
    df["ts"] = df["ts"].astype(int)
    df["qty"] = df["qty"].astype(float)
    df["price"] = df["price"].astype(float)
    df["side"] = df["side"].astype(str)
    df["symbol"] = df["symbol"].astype(str)
    df["dt"] = pd.to_datetime(df["ts"], unit="s")
    df["date"] = df["dt"].dt.date
    return df


def get_starting_cash(default=100000.0):
    c = _conn()
    cur = c.cursor()
    try:
        cur.execute("SELECT starting_cash FROM settings WHERE id=1")
        row = cur.fetchone()
        c.close()
        if row is None:
            return float(default)
        return float(row[0])
    except Exception:
        c.close()
        return float(default)


def build_trade_blotter_avg_cost(df_trades, starting_cash):
    """
    Simulates avg-cost accounting to produce realized PnL for sells
    and an equity series using cash only (mark-to-market added separately).
    """
    cash = float(starting_cash)

    # positions: symbol -> (qty, avg_cost)
    pos_qty = {}
    pos_avg = {}

    rows = []
    i = 0
    while i < len(df_trades):
        r = df_trades.iloc[i]
        sym = str(r["symbol"]).upper()
        side = str(r["side"]).lower()
        qty = float(r["qty"])
        px = float(r["price"])

        realized = 0.0

        if side == "buy":
            cost = qty * px
            cash = cash - cost

            if sym not in pos_qty:
                pos_qty[sym] = qty
                pos_avg[sym] = px
            else:
                old_q = float(pos_qty[sym])
                old_avg = float(pos_avg[sym])
                new_q = old_q + qty
                new_avg = (old_q * old_avg + qty * px) / new_q
                pos_qty[sym] = new_q
                pos_avg[sym] = new_avg

        else:  # sell
            if sym not in pos_qty:
                # ignore invalid sell (shouldn't happen if broker blocked)
                i += 1
                continue

            old_q = float(pos_qty[sym])
            old_avg = float(pos_avg[sym])

            sell_q = qty
            if sell_q > old_q:
                sell_q = old_q

            proceeds = sell_q * px
            cash = cash + proceeds

            realized = (px - old_avg) * sell_q

            new_q = old_q - sell_q
            if new_q <= 0:
                del pos_qty[sym]
                del pos_avg[sym]
            else:
                pos_qty[sym] = new_q
                pos_avg[sym] = old_avg

        rows.append({
            "dt": r["dt"],
            "date": r["date"],
            "symbol": sym,
            "side": side,
            "qty": qty,
            "price": px,
            "cash_after": cash,
            "realized_pl": realized
        })
        i += 1

    blotter = pd.DataFrame(rows)
    return blotter


def equity_curve_from_trades(df_trades, price_map=None):
    """
    Returns:
      - equity_df: date-level equity curve
      - stats dict
      - blotter df
      - current_positions df
    price_map: dict like {"AAPL": 195.2} to mark positions. If None, uses last trade price per symbol.
    """
    if df_trades is None or len(df_trades) == 0:
        return None, {}, None, None

    starting_cash = get_starting_cash(100000.0)
    blotter = build_trade_blotter_avg_cost(df_trades, starting_cash)

    # Build end-of-day positions + equity
    cash = float(starting_cash)
    pos_qty = {}
    pos_avg = {}

    # last trade price per symbol (fallback mark)
    last_px = {}
    i = 0
    while i < len(df_trades):
        r = df_trades.iloc[i]
        last_px[str(r["symbol"]).upper()] = float(r["price"])
        i += 1

    # iterate trades and snapshot per day
    equity_rows = []
    dates = df_trades["date"].tolist()

    i = 0
    current_date = None
    while i < len(df_trades):
        r = df_trades.iloc[i]
        sym = str(r["symbol"]).upper()
        side = str(r["side"]).lower()
        qty = float(r["qty"])
        px = float(r["price"])
        d = r["date"]

        if current_date is None:
            current_date = d

        # Apply trade
        if side == "buy":
            cash = cash - qty * px
            if sym not in pos_qty:
                pos_qty[sym] = qty
                pos_avg[sym] = px
            else:
                old_q = float(pos_qty[sym])
                old_avg = float(pos_avg[sym])
                new_q = old_q + qty
                new_avg = (old_q * old_avg + qty * px) / new_q
                pos_qty[sym] = new_q
                pos_avg[sym] = new_avg
        else:
            if sym in pos_qty:
                old_q = float(pos_qty[sym])
                old_avg = float(pos_avg[sym])
                sell_q = qty
                if sell_q > old_q:
                    sell_q = old_q
                cash = cash + sell_q * px
                new_q = old_q - sell_q
                if new_q <= 0:
                    del pos_qty[sym]
                    del pos_avg[sym]
                else:
                    pos_qty[sym] = new_q
                    pos_avg[sym] = old_avg

        # If next trade is a new day OR last trade, snapshot EOD equity
        next_is_new_day = False
        if i == len(df_trades) - 1:
            next_is_new_day = True
        else:
            next_d = df_trades.iloc[i + 1]["date"]
            if next_d != d:
                next_is_new_day = True

        if next_is_new_day:
            # Mark-to-market positions
            mv = 0.0
            for s in pos_qty:
                q = float(pos_qty[s])
                mark = None
                if price_map is not None and s in price_map:
                    mark = float(price_map[s])
                else:
                    mark = float(last_px.get(s, float(pos_avg[s])))
                mv += q * mark

            equity = cash + mv
            equity_rows.append({"date": d, "cash": cash, "positions_value": mv, "equity": equity})

        i += 1

    equity_df = pd.DataFrame(equity_rows)
    equity_df["equity"] = equity_df["equity"].astype(float)
    equity_df["ret"] = equity_df["equity"].pct_change().fillna(0.0)

    # Stats
    total_return = (equity_df["equity"].iloc[-1] / equity_df["equity"].iloc[0]) - 1.0

    peak = equity_df["equity"].cummax()
    dd = (equity_df["equity"] / peak) - 1.0
    max_dd = float(dd.min())

    # Sharpe (daily)
    r = equity_df["ret"]
    r_std = float(r.std())
    sharpe = 0.0
    if r_std > 0:
        sharpe = float((r.mean() / r_std) * math.sqrt(252))

    # Win rate / profit factor from realized PnL
    realized = blotter["realized_pl"]
    wins = realized[realized > 0]
    losses = realized[realized < 0]
    win_rate = 0.0
    if len(wins) + len(losses) > 0:
        win_rate = float(len(wins) / (len(wins) + len(losses)))

    profit_factor = 0.0
    if float(abs(losses.sum())) > 0:
        profit_factor = float(wins.sum() / abs(losses.sum()))

    avg_win = float(wins.mean()) if len(wins) > 0 else 0.0
    avg_loss = float(losses.mean()) if len(losses) > 0 else 0.0

    stats = {
        "starting_cash": float(equity_df["equity"].iloc[0]),
        "ending_equity": float(equity_df["equity"].iloc[-1]),
        "total_return": float(total_return),
        "max_drawdown": float(max_dd),
        "sharpe_daily": float(sharpe),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "num_trades": int(len(df_trades))
    }

    # Current positions snapshot
    pos_rows = []
    for s in pos_qty:
        q = float(pos_qty[s])
        avg = float(pos_avg[s])
        mark = None
        if price_map is not None and s in price_map:
            mark = float(price_map[s])
        else:
            mark = float(last_px.get(s, avg))
        upl = (mark - avg) * q
        pos_rows.append({"symbol": s, "qty": q, "avg_cost": avg, "mark": mark, "unrealized_pl": upl})

    pos_df = pd.DataFrame(pos_rows) if len(pos_rows) > 0 else pd.DataFrame(columns=["symbol","qty","avg_cost","mark","unrealized_pl"])

    return equity_df, stats, blotter, pos_df