import pandas as pd
import hashlib
from pathlib import Path

USER_DB = Path("storage/users.csv")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def load_users():
    if not USER_DB.exists():
        return pd.DataFrame(columns=["username", "password"])
    return pd.read_csv(USER_DB)


def save_user(username: str, password: str) -> bool:
    users = load_users()

    if username in users["username"].values:
        return False

    new_user = pd.DataFrame(
        [{
            "username": username,
            "password": hash_password(password)
        }]
    )

    users = pd.concat([users, new_user], ignore_index=True)
    users.to_csv(USER_DB, index=False)
    return True


def authenticate(username: str, password: str) -> bool:
    users = load_users()
    hashed = hash_password(password)

    match = users[
        (users["username"] == username) &
        (users["password"] == hashed)
    ]

    return not match.empty
