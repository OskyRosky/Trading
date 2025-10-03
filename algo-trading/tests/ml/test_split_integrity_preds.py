import pandas as pd
from pathlib import Path

SPLIT = pd.Timestamp("2023-01-01", tz="UTC")
DATA = Path("/Users/sultan/Trading/data")
DS_DIR = DATA/"ml"/"datasets"
PREDS_DIR = DATA/"ml"/"preds"

def test_preds_only_in_test_and_no_overlap_with_train():
    for p in PREDS_DIR.glob("*_preds.csv"):
        sym = p.stem.replace("_preds","")
        preds = pd.read_csv(p, parse_dates=["date"])
        preds["date"] = pd.to_datetime(preds["date"], utc=True)
        assert (preds["date"] >= SPLIT).all()
        ds = pd.read_parquet(DS_DIR/f"symbol={sym}"/"interval=1d"/"data.parquet")
        ds = ds.sort_values("date").reset_index(drop=True)
        ds["date"] = pd.to_datetime(ds["date"], utc=True)
        train_dates = set(ds.loc[ds["date"] < SPLIT,"date"])
        test_dates  = set(preds["date"])
        assert len(train_dates) > 0
        assert len(test_dates & train_dates) == 0
