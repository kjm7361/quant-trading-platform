import json
import os
from datetime import datetime, timezone


HISTORY_PATH = "storage/alert_history.json"


def _load_all():
    if not os.path.exists(HISTORY_PATH):
        return {}
    try:
        with open(HISTORY_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_all(data):
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_history(username):
    data = _load_all()
    return data.get(username, [])


def add_notification(username, ticker, message, alert_index):
    """
    Store a notification event.
    """
    data = _load_all()
    lst = data.get(username, [])
    lst.insert(0, {  # newest on top
        "time_utc": _now_iso(),
        "ticker": str(ticker).upper(),
        "message": str(message),
        "alert_index": int(alert_index),
    })
    # Keep last 200
    lst = lst[:200]
    data[username] = lst
    _save_all(data)


def was_recently_triggered(username, alert_index, within_minutes=120):
    """
    Returns True if this alert_index triggered in last X minutes (anti-spam).
    """
    hist = get_history(username)
    if len(hist) == 0:
        return False

    cutoff_seconds = within_minutes * 60

    for item in hist:
        if int(item.get("alert_index", -1)) != int(alert_index):
            continue

        t = item.get("time_utc", "")
        try:
            dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - dt).total_seconds()
            if age <= cutoff_seconds:
                return True
        except Exception:
            continue

    return False


def clear_history(username):
    data = _load_all()
    data[username] = []
    _save_all(data)
