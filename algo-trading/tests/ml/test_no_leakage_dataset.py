import pandas as pd
from pathlib import Path
import numpy as np

DATA = Path("/Users/sultan/Trading/data")
DS_DIR = DATA/"ml"/"datasets"

def test_label_uses_tplus1_close_and_last_is_nan():
    for p in DS_DIR.glob("symbol=*/interval=1d/data.parquet"):
        df = pd.read_parquet(p).sort_values("date").reset_index(drop=True)
        assert {"date","close","ret_fwd_1d","y_up"}.issubset(df.columns)
        df["close_next"] = df["close"].shift(-1)
        df["ret_chk"] = df["close_next"]/df["close"] - 1.0
        tol = 1e-8
        eq_mask = (df["ret_fwd_1d"].fillna(0) - df["ret_chk"].fillna(0)).abs() < tol
        assert eq_mask.iloc[:-1].all()
        assert pd.isna(df["ret_fwd_1d"].iloc[-1])
        y_up_chk = (df["ret_fwd_1d"] > 0).astype(int)
        y_up_diff = (df["y_up"].fillna(-1) - y_up_chk.fillna(-1)).abs().sum()
        assert y_up_diff == 0
