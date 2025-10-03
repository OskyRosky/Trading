from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import datetime as dt

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score

DATA = Path("/Users/sultan/Trading/data")
DS_DIR = DATA / "ml" / "datasets"
OUT = DATA / "checks" / "reports"
OUT.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "ret_pct","sma_7","sma_20","ema_12","ema_26","rsi_14","atr_14","adx_14",
    "bb_ma_20_2","bb_u_20_2","bb_l_20_2","volume","trades","sma_spread_7_20","ema_spread_12_26"
]

def strat_returns(y_pred: pd.Series, ret_fwd_1d: pd.Series, fee_bps: float=2.0) -> pd.Series:
    fee = fee_bps/10000.0
    # daily strategy return: long if 1 else 0, includes entry+exit fees per trade change
    pos = y_pred.astype(int)
    ret = pos * ret_fwd_1d
    # penalizar cambios de señal (turnover)
    turn = (pos.diff().abs().fillna(0))
    ret -= turn * fee
    return ret

def fold_metrics(y_true, y_prob, y_pred, ret_strat):
    out = {}
    out["acc"] = accuracy_score(y_true, y_pred)
    with np.errstate(divide='ignore', invalid='ignore'):
        out["precision"] = precision_score(y_true, y_pred, zero_division=0)
        out["recall"] = recall_score(y_true, y_pred, zero_division=0)
    try:
        out["auc"] = roc_auc_score(y_true, y_prob)
    except Exception:
        out["auc"] = np.nan
    eq = (1 + ret_strat.fillna(0)).cumprod()
    dd = (eq/eq.cummax() - 1).min()
    out["maxdd"] = float(dd) if np.isfinite(dd) else np.nan
    # Sharpe: mean/std * sqrt(252)
    sr = ret_strat.mean() / (ret_strat.std() + 1e-9) * np.sqrt(252)
    out["sharpe"] = float(sr) if np.isfinite(sr) else np.nan
    return out

def walkforward_symbol(symbol: str, test_window_days: int=90, min_train_days: int=400, fee_bps: float=2.0):
    fp = DS_DIR / f"symbol={symbol}" / "interval=1d" / "data.parquet"
    df = pd.read_parquet(fp)
    df = df.sort_values("date").reset_index(drop=True)

    # aseguramos sin nulos en features
    df = df.dropna(subset=FEATURES + ["y_up","ret_fwd_1d"]).reset_index(drop=True)

    folds = []
    start_idx = 0
    # mínimo entrenamiento en días
    while True:
        # rango temporal
        train_end_date = df.loc[start_idx, "date"] + pd.Timedelta(days=min_train_days-1)
        test_end_date  = train_end_date + pd.Timedelta(days=test_window_days)
        train = df[(df["date"] <= train_end_date)]
        test  = df[(df["date"] >  train_end_date) & (df["date"] <= test_end_date)]

        if len(test) < 10:  # no hay suficiente test para una métrica estable
            break
        if len(train) < min_train_days:
            # desplaza el inicio hasta alcanzar min_train_days
            start_idx += 1
            continue

        Xtr, ytr = train[FEATURES].values, train["y_up"].values
        Xte, yte = test[FEATURES].values, test["y_up"].values

        m = LogisticRegression(max_iter=200, n_jobs=None)
        m.fit(Xtr, ytr)
        prob = m.predict_proba(Xte)[:,1]
        pred = (prob >= 0.5).astype(int)

        rstr = strat_returns(pd.Series(pred, index=test.index), test["ret_fwd_1d"], fee_bps=fee_bps)
        met = fold_metrics(yte, prob, pred, rstr)
        row = {
            "symbol": symbol,
            "train_start": train["date"].iloc[0],
            "train_end": train["date"].iloc[-1],
            "test_start": test["date"].iloc[0],
            "test_end": test["date"].iloc[-1],
            "n_train": len(train),
            "n_test": len(test),
            "fee_bps": fee_bps,
            **met
        }
        folds.append(row)

        # avanzar ventana: mover train_end hacia adelante en bloques de test_window_days
        start_idx = df.index[df["date"] > test_end_date][0] if any(df["date"] > test_end_date) else len(df)
        if start_idx >= len(df)-1:
            break

    return pd.DataFrame(folds)

def main():
    # lee símbolos disponibles en datasets
    syms = [p.name.split("=")[1] for p in (DS_DIR.glob("symbol=*"))]
    all_res = []
    for s in sorted(syms):
        try:
            res = walkforward_symbol(s, test_window_days=90, min_train_days=400, fee_bps=2.0)
            if not res.empty:
                out_fp = OUT / f"wf_metrics_{s}.csv"
                res.to_csv(out_fp, index=False)
                print(f"[OK] {s} folds={len(res)} → {out_fp}")
                all_res.append(res)
            else:
                print(f"[WARN] {s} sin folds suficientes")
        except Exception as e:
            print(f"[ERROR] {s}: {e}")

    if not all_res:
        print("No se generaron resultados.")
        return

    all_df = pd.concat(all_res, ignore_index=True)
    # resumen por símbolo
    summary = (all_df
               .groupby("symbol", as_index=False)[["acc","precision","recall","auc","sharpe","maxdd"]]
               .mean(numeric_only=True))
    summary = summary.sort_values("sharpe", ascending=False)

    today = dt.datetime.now(dt.UTC).date().isoformat()
    out_csv = OUT / "wf_summary.csv"
    summary.to_csv(out_csv, index=False)

    out_md = OUT / "wf_summary.md"
    with open(out_md, "w") as f:
        f.write(f"# Walk-Forward summary — {today}\n\n")
        f.write(summary.to_markdown(index=False))

    print("Resumen WF:")
    print("-", out_csv)
    print("-", out_md)

if __name__ == "__main__":
    main()
