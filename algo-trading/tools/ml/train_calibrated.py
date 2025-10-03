from __future__ import annotations
from pathlib import Path
import pandas as pd, numpy as np, json, datetime as dt
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV

DATA = Path("/Users/sultan/Trading/data")
DS_DIR = DATA/"ml"/"datasets"
OUT_MET = DATA/"checks"/"reports"
OUT_MET.mkdir(parents=True, exist_ok=True)
MODELS_DIR = DATA/"ml"/"models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
PREDS_DIR = DATA/"ml"/"preds"
PREDS_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "ret_pct","sma_7","sma_20","ema_12","ema_26","rsi_14","atr_14","adx_14",
    "bb_ma_20_2","bb_u_20_2","bb_l_20_2","volume","trades","sma_spread_7_20","ema_spread_12_26"
]
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")

def run_symbol(sym:str):
    fp = DS_DIR/f"symbol={sym}"/"interval=1d"/"data.parquet"
    df = pd.read_parquet(fp).sort_values("date")
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.dropna(subset=FEATURES+["y_up"])
    train = df[df["date"] <  SPLIT].copy()
    test  = df[df["date"] >= SPLIT].copy()
    if len(train)<200 or len(test)<50: 
        return None
    Xtr,ytr = train[FEATURES].values, train["y_up"].values
    Xte,yte = test[FEATURES].values,  test["y_up"].values
    base = LogisticRegression(max_iter=200)
    clf = CalibratedClassifierCV(base, method="sigmoid", cv=5)
    clf.fit(Xtr, ytr)
    p_cal = clf.predict_proba(Xte)[:,1]
    out = test[["date","y_up"]].copy()
    out["symbol"] = sym
    out["prob_up_cal"] = p_cal
    preds_path = PREDS_DIR/f"{sym}_preds_cal.csv"
    out.to_csv(preds_path, index=False)
    meta = {
        "symbol": sym,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "split": str(SPLIT.date()),
        "model": "LR+Calibrated(sigmoid,cv=5)",
        "features": FEATURES
    }
    print(json.dumps(meta))
    return preds_path

def main():
    syms = [p.name.split("=")[1] for p in DS_DIR.glob("symbol=*")]
    for s in sorted(syms):
        try:
            run_symbol(s)
        except Exception as e:
            print(f"ERR {s}: {e}")

if __name__=="__main__":
    main()
