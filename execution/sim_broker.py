import sqlite3
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "storage" / "sim_trading.db"


def _ensure_storage_dir():
    p = DB_PATH.parent
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)


def init_db():
    _ensure_storage_dir()

    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS account (
            id INTEGER PRIMARY KEY,
            cash REAL NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            symbol TEXT PRIMARY KEY,
            qty REAL NOT NULL,
            avg_price REAL NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            qty REAL NOT NULL,
            price REAL NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            starting_cash REAL NOT NULL
        )
        """)

        # seed settings
        cur.execute("SELECT COUNT(*) FROM settings")
        m = cur.fetchone()[0]
        if m == 0:
            cur.execute("INSERT INTO settings (id, starting_cash) VALUES (1, 100000.0)")

        # seed account
        cur.execute("SELECT COUNT(*) FROM account")
        n = cur.fetchone()[0]
        if n == 0:
            cur.execute("INSERT INTO account (id, cash) VALUES (1, 100000.0)")


def reset_account(starting_cash=100000.0):
    _ensure_storage_dir()

    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()
        cur.execute("DELETE FROM trades")
        cur.execute("DELETE FROM positions")
        cur.execute("DELETE FROM account")
        cur.execute("INSERT INTO account (id, cash) VALUES (1, ?)", (float(starting_cash),))

        cur.execute("DELETE FROM settings")
        cur.execute("INSERT INTO settings (id, starting_cash) VALUES (1, ?)", (float(starting_cash),))


def get_starting_cash(default=100000.0):
    _ensure_storage_dir()

    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()
        try:
            cur.execute("SELECT starting_cash FROM settings WHERE id=1")
            row = cur.fetchone()
            if row is None:
                return float(default)
            return float(row[0])
        except Exception:
            return float(default)


def get_cash():
    _ensure_storage_dir()

    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()
        cur.execute("SELECT cash FROM account WHERE id=1")
        row = cur.fetchone()
        if row is None:
            return 0.0
        return float(row[0])


def set_cash(new_cash):
    _ensure_storage_dir()

    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()
        cur.execute("UPDATE account SET cash=? WHERE id=1", (float(new_cash),))


def get_positions():
    _ensure_storage_dir()

    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()
        cur.execute("SELECT symbol, qty, avg_price FROM positions ORDER BY symbol")
        rows = cur.fetchall()

    out = []
    i = 0
    while i < len(rows):
        out.append({"symbol": rows[i][0], "qty": float(rows[i][1]), "avg_price": float(rows[i][2])})
        i += 1
    return out


def _get_position(symbol):
    _ensure_storage_dir()

    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()
        cur.execute("SELECT symbol, qty, avg_price FROM positions WHERE symbol=?", (symbol,))
        return cur.fetchone()


def _upsert_position(symbol, qty, avg_price):
    _ensure_storage_dir()

    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()
        cur.execute("""
        INSERT INTO positions(symbol, qty, avg_price) VALUES(?,?,?)
        ON CONFLICT(symbol) DO UPDATE SET qty=excluded.qty, avg_price=excluded.avg_price
        """, (symbol, float(qty), float(avg_price)))


def _delete_position(symbol):
    _ensure_storage_dir()

    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()
        cur.execute("DELETE FROM positions WHERE symbol=?", (symbol,))


def log_trade(symbol, side, qty, price):
    _ensure_storage_dir()

    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()
        cur.execute(
            "INSERT INTO trades(ts, symbol, side, qty, price) VALUES(?,?,?,?,?)",
            (int(time.time()), symbol, side, float(qty), float(price))
        )


def list_trades(limit=100):
    _ensure_storage_dir()

    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()
        cur.execute("""
        SELECT ts, symbol, side, qty, price
        FROM trades
        ORDER BY ts DESC
        LIMIT ?
        """, (int(limit),))
        rows = cur.fetchall()

    out = []
    i = 0
    while i < len(rows):
        out.append({
            "ts": int(rows[i][0]),
            "symbol": rows[i][1],
            "side": rows[i][2],
            "qty": float(rows[i][3]),
            "price": float(rows[i][4])
        })
        i += 1
    return out


def place_market_order(symbol, qty, side, fill_price):
    symbol = str(symbol).upper().strip()
    side = str(side).lower().strip()
    qty = float(qty)
    price = float(fill_price)

    if qty <= 0:
        return {"ok": False, "error": "Qty must be > 0"}

    cash = get_cash()
    pos = _get_position(symbol)

    if side == "buy":
        cost = qty * price
        if cost > cash:
            return {"ok": False, "error": "Insufficient cash"}

        if pos is None:
            new_qty = qty
            new_avg = price
        else:
            old_qty = float(pos[1])
            old_avg = float(pos[2])
            new_qty = old_qty + qty
            new_avg = (old_qty * old_avg + qty * price) / new_qty

        set_cash(cash - cost)
        _upsert_position(symbol, new_qty, new_avg)
        log_trade(symbol, "buy", qty, price)
        return {"ok": True, "symbol": symbol, "side": "buy", "qty": qty, "price": price}

    if side == "sell":
        if pos is None:
            return {"ok": False, "error": "No position to sell"}

        old_qty = float(pos[1])
        old_avg = float(pos[2])

        if qty > old_qty:
            return {"ok": False, "error": "Not enough shares"}

        proceeds = qty * price
        set_cash(cash + proceeds)

        new_qty = old_qty - qty
        if new_qty == 0:
            _delete_position(symbol)
        else:
            _upsert_position(symbol, new_qty, old_avg)

        log_trade(symbol, "sell", qty, price)
        realized = (price - old_avg) * qty
        return {"ok": True, "symbol": symbol, "side": "sell", "qty": qty, "price": price, "realized_pl": realized}

    return {"ok": False, "error": "Side must be buy or sell"}