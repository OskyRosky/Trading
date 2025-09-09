from __future__ import annotations
import pandas as pd

def normalize_klines_to_df(klines: list[list]) -> pd.DataFrame:
    cols = ["open_time","open","high","low","close","volume","close_time","quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"]
    df = pd.DataFrame(klines, columns=cols)
    for c in ["open","high","low","close","volume","quote_volume","taker_buy_base","taker_buy_quote"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["trades"] = pd.to_numeric(df["trades"], errors="coerce").astype("Int64")
    df["date"] = pd.to_datetime(df["close_time"], unit="ms", utc=True).dt.normalize()
    return df[["date","open","high","low","close","volume","trades","quote_volume","close_time"]]

def validate_ohlcv_rules(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    ok1 = df["low"] <= df[["open","close","high"]].min(axis=1)
    ok2 = df["high"] >= df[["open","close","low"]].max(axis=1)
    ok3 = (df["volume"] >= 0) & (df["trades"].fillna(0) >= 0)
    df = df[ ok1 & ok2 & ok3 ]
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return df
