from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import datetime as dt
import glob

DATA = Path("/Users/sultan/Trading/data")
REP = DATA / "checks" / "reports"
SIG = DATA / "ml" / "signals"
PLAN = DATA / "ml" / "trade_plan"
REP.mkdir(parents=True, exist_ok=True)

def latest_file(pattern: str) -> Path | None:
    files = sorted(glob.glob(pattern))
    return Path(files[-1]) if files else None

def main():
    today = dt.datetime.now(dt.UTC).date().isoformat()

    sig_fp = latest_file(str(SIG / "signals_*.csv"))
    plan_fp = latest_file(str(PLAN / "plan_*.csv"))
    bt_fp   = DATA / "checks" / "reports" / "ml_bt_metrics_all.csv"

    if sig_fp is None or plan_fp is None:
        raise SystemExit("Faltan señales o plan: ejecuta export_signals_from_preds.py y make_trade_plan.py")

    sig = pd.read_csv(sig_fp, parse_dates=["date"])
    plan = pd.read_csv(plan_fp)
    bt = pd.read_csv(bt_fp) if bt_fp.exists() else pd.DataFrame()

    sig["date"] = pd.to_datetime(sig["date"], utc=True)
    latest_date = sig["date"].max().date().isoformat()

    longs = plan[plan["side"] == "LONG"].copy()
    flats = plan[plan["side"] != "LONG"].copy()

    top5 = plan.sort_values("confidence", ascending=False).head(5).copy()
    top5.loc[:, "weight_pct"] = (top5["weight"] * 100).round(2)

    if not bt.empty:
        perf = bt[["symbol", "CAGR", "Sharpe", "MaxDD", "threshold", "fee_bps"]].copy()
        perf = perf.rename(columns={"threshold":"thr"})
        # último set (si se reescribe cada día, basta ordenar por símbolo y tomar última fila por símbolo)
        perf = perf.sort_values(["symbol"]).drop_duplicates(subset=["symbol"], keep="last")
    else:
        perf = pd.DataFrame(columns=["symbol","CAGR","Sharpe","MaxDD","thr","fee_bps"])

    # Ensamble tabular para CSV
    summary_rows = []
    for _, r in plan.sort_values("confidence", ascending=False).iterrows():
        sym = r["symbol"]
        p = perf[perf["symbol"] == sym].head(1)
        row = {
            "report_date": today,
            "signals_date": latest_date,
            "symbol": sym,
            "side": r["side"],
            "prob_up": round(float(r["prob_up"]), 4),
            "thr": round(float(r["thr"]), 3),
            "confidence": round(float(r["confidence"]), 4),
            "weight": round(float(r.get("weight", 0.0)), 6),
            "CAGR": round(float(p["CAGR"].values[0]), 4) if not p.empty else np.nan,
            "Sharpe": round(float(p["Sharpe"].values[0]), 4) if not p.empty else np.nan,
            "MaxDD": round(float(p["MaxDD"].values[0]), 4) if not p.empty else np.nan,
        }
        summary_rows.append(row)
    summary_df = pd.DataFrame(summary_rows)

    md_path = REP / f"daily_summary_{today}.md"
    csv_path = REP / f"daily_summary_{today}.csv"

    # Markdown
    with open(md_path, "w") as f:
        f.write(f"# Resumen diario — {today} (UTC)\n\n")
        f.write(f"**Fecha de señales:** {latest_date}\n\n")
        f.write(f"- LONGs: {len(longs)}\n")
        f.write(f"- FLATs: {len(flats)}\n\n")

        f.write("## Top 5 por confianza\n\n")
        if len(top5):
            f.write(top5[["symbol","side","prob_up","thr","confidence","weight_pct"]].to_markdown(index=False))
        else:
            f.write("_Sin señales._")
        f.write("\n\n")

        f.write("## Plan completo\n\n")
        f.write(plan[["symbol","side","prob_up","thr","confidence","weight"]].sort_values("confidence", ascending=False).to_markdown(index=False))
        f.write("\n\n")

        f.write("## Métricas ML por símbolo (última corrida)\n\n")
        if len(perf):
            f.write(perf[["symbol","CAGR","Sharpe","MaxDD","thr","fee_bps"]].sort_values("Sharpe", ascending=False).to_markdown(index=False))
        else:
            f.write("_No hay métricas de backtest ML cargadas._\n")

    # CSV
    summary_df.to_csv(csv_path, index=False)

    # “latest” (copias prácticas)
    (REP / "daily_summary_latest.md").write_text(md_path.read_text())
    summary_df.to_csv(REP / "daily_summary_latest.csv", index=False)

    print("Resumen diario escrito:")
    print("-", md_path)
    print("-", csv_path)
    print("-", REP / "daily_summary_latest.md")
    print("-", REP / "daily_summary_latest.csv")

if __name__ == "__main__":
    main()
