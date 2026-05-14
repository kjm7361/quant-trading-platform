import json
import os


WATCHLIST_PATH = "storage/watchlists.json"


def _load_all():
    if not os.path.exists(WATCHLIST_PATH):
        return {}
    try:
        with open(WATCHLIST_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_all(data):
    # Ensure storage folder exists
    os.makedirs(os.path.dirname(WATCHLIST_PATH), exist_ok=True)
    with open(WATCHLIST_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_watchlist(username):
    data = _load_all()
    items = data.get(username, [])
    # ensure unique + uppercase
    out = []
    seen = set()
    for t in items:
        tt = str(t).strip().upper()
        if tt and tt not in seen:
            out.append(tt)
            seen.add(tt)
    return out


def add_to_watchlist(username, ticker):
    t = str(ticker).strip().upper()
    if t == "":
        return

    data = _load_all()
    items = data.get(username, [])

    t_norm = t
    if t_norm not in items:
        items.append(t_norm)

    data[username] = items
    _save_all(data)


def remove_from_watchlist(username, ticker):
    t = str(ticker).strip().upper()
    data = _load_all()
    items = data.get(username, [])

    items = [x for x in items if str(x).strip().upper() != t]
    data[username] = items
    _save_all(data)
