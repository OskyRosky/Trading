from __future__ import annotations
import sys, json
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
import joblib
import yaml

BASE = Path("/Users/sultan/Trading/algo-trading")
DATA = Path("/Users/sultan/Trading/data")

with open(BASE/"configs"/"ml.yml","r") as f:
    ML = yaml.safe_load(f)
FEATURES = ML["features"]
SPLIT_DATE = pd.Timestamp(ML["split_date"], tz="UTC")

def load_symbol_df(sym: str) -> pd.DataFrame:
    path = DATA/"ml"/"datasets"/f"symbol={sym}"/"interval=1d"/"data.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No dataset para {sym}: {path}")
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df.sort_values("date").reset_index(drop=True)

def split_train_test(df: pd.DataFrame):
    train = df[df["date"] < SPLIT_DATE].copy()
    test  = df[df["date"] >= SPLIT_DATE].copy()
    return train, test

def train_one_symbol(sym: str) -> dict:
    df = load_symbol_df(sym)
    cols = ["date","y_up"] + [c for c in FEATURES if c in df.columns]
    df = df[cols].dropna().copy()
    if df["y_up"].nunique() < 2:
        raise RuntimeError(f"{sym}: y_up sin variabilidad")
    train, test = split_train_test(df)
    if len(train)==0 or len(test)==0:
        raise RuntimeError(f"{sym}: split vacío; revisa split_date")
    X_tr, y_tr = train[FEATURES], train["y_up"]
    X_te, y_te = test[FEATURES], test["y_up"]

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=200, n_jobs=None))
    ])
    pipe.fit(X_tr, y_tr)

    proba = pipe.predict_proba(X_te)[:,1]
    pred  = (proba >= 0.5).astype(int)

    metrics = {
        "symbol": sym,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "acc": float(accuracy_score(y_te, pred)),
        "precision": float(precision_score(y_te, pred, zero_division=0)),
        "recall": float(recall_score(y_te, pred, zero_division=0)),
        "auc": float(roc_auc_score(y_te, proba)) if y_te.nunique()==2 else np.nan,
        "split_date": str(SPLIT_DATE.date()),
        "features_used": [c for c in FEATURES if c in df.columns],
    }

    out_models = DATA/"ml"/"models"
    out_models.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, out_models/f"lr_{sym}.joblib")

    out_preds = DATA/"ml"/"preds"
    out_preds.mkdir(parents=True, exist_ok=True)
    pred_df = test[["date"]].copy()
    pred_df["symbol"] = sym
    pred_df["y_true"] = y_te.values
    pred_df["prob_up"] = proba
    pred_df["pred_up"] = pred
    pred_df.to_csv(out_preds/f"{sym}_preds.csv", index=False)

    out_reports = DATA/"checks"/"reports"
    out_reports.mkdir(parents=True, exist_ok=True)
    met_path = out_reports/f"ml_metrics_{sym}.csv"
    pd.DataFrame([metrics]).to_csv(met_path, index=False)

    print(json.dumps({"trained": sym, "metrics_csv": str(met_path), "model": str(out_models/f'lr_{sym}.joblib'), "preds_csv": str(out_preds/f'{sym}_preds.csv')}, indent=2))
    return metrics

def main():
    symbols = yaml.safe_load((BASE/"configs"/"symbols.yml").read_text())["symbol_map"].keys()
    all_m = []
    for sym in symbols:
        try:
            m = train_one_symbol(sym)
            all_m.append(m)
        except Exception as e:
            print(json.dumps({"error_symbol": sym, "error": str(e)}))
    if all_m:
        out_reports = DATA/"checks"/"reports"
        pd.DataFrame(all_m).to_csv(out_reports/"ml_metrics_all.csv", index=False)
        print(str(out_reports/"ml_metrics_all.csv"))

if __name__ == "__main__":
    main()
