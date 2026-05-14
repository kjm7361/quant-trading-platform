import json
import os


ALERTS_PATH = "storage/alerts.json"


def _load_all():
    if not os.path.exists(ALERTS_PATH):
        return {}
    try:
        with open(ALERTS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_all(data):
    os.makedirs(os.path.dirname(ALERTS_PATH), exist_ok=True)
    with open(ALERTS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_alerts(username):
    data = _load_all()
    return data.get(username, [])


def add_alert(username, ticker, above=None, below=None, pct_above=None):
    alert = {
        "ticker": str(ticker).strip().upper(),
        "above": above,
        "below": below,
        "pct_above": pct_above
    }

    data = _load_all()
    lst = data.get(username, [])
    lst.append(alert)
    data[username] = lst
    _save_all(data)


def remove_alert(username, idx):
    data = _load_all()
    lst = data.get(username, [])
    if 0 <= idx < len(lst):
        lst.pop(idx)
    data[username] = lst
    _save_all(data)
