import pandas as pd


def df_to_csv_bytes(df: pd.DataFrame):
    if df is None:
        return b""
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)
    return df.to_csv(index=True).encode("utf-8")


def series_to_csv_bytes(s: pd.Series, name="value"):
    if s is None:
        return b""
    s = pd.Series(s).copy()
    if s.name is None:
        s.name = name
    df = s.to_frame()
    return df.to_csv(index=True).encode("utf-8")
