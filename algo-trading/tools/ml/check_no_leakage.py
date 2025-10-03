from pathlib import Path
import pandas as pd

DATA = Path("/Users/sultan/Trading/data")
DS_DIR = DATA/"ml"/"datasets"
ok = True
msgs = []

for p in DS_DIR.glob("symbol=*/interval=1d/data.parquet"):
    df = pd.read_parquet(p).sort_values("date").reset_index(drop=True)
    sym = p.parts[-3].split("=")[1]
    df["close_next"] = df["close"].shift(-1)
    df["ret_chk"] = df["close_next"]/df["close"] - 1.0
    tol = 1e-8
    a = (df["ret_fwd_1d"].fillna(0) - df["ret_chk"].fillna(0)).abs() < tol
    if not a.iloc[:-1].all() or not pd.isna(df["ret_fwd_1d"].iloc[-1]):
        ok = False
        msgs.append(f"[LABEL] mismatch/last not NaN: {sym}")
    if ((df["y_up"] > 0) != (df["ret_fwd_1d"] > 0)).any():
        ok = False
        msgs.append(f"[Y_UP] mismatch: {sym}")

print("OK" if ok else "FAIL")
for m in msgs:
    print(m)
