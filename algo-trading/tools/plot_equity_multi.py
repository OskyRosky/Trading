from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

OUT_DIR = Path("/Users/sultan/Trading/data/checks/figures")
CSV_DIR = Path("/Users/sultan/Trading/data/checks/reports")
OUT_DIR.mkdir(parents=True, exist_ok=True)
CSV_DIR.mkdir(parents=True, exist_ok=True)

def run_bt(symbol: str, start: str, fee_bps: float, use_rsi: bool) -> Path:
    csv = CSV_DIR / f"equity_{symbol}.csv"
    args = [sys.executable, "tools/backtest_sma.py", "--symbol", symbol, "--start", start, "--fee_bps", str(fee_bps), "--out", str(csv)]
    if use_rsi is False:
        args.append("--no_rsi")
    subprocess.run(args, check=True)
    return csv

def main():
    p = argparse.ArgumentParser(description="Plot multi equity curves")
    p.add_argument("--symbols", nargs="+", required=True)
    p.add_argument("--start", default="2020-01-01")
    p.add_argument("--fee_bps", type=float, default=2.0)
    p.add_argument("--use_rsi", action="store_true")
    args = p.parse_args()

    plt.figure(figsize=(12,6))
    for s in args.symbols:
        csv = run_bt(s, args.start, args.fee_bps, args.use_rsi)
        df = pd.read_csv(csv, parse_dates=["date"])
        plt.plot(df["date"], df["equity"], label=s)
    plt.title("Equity curves")
    plt.xlabel("Fecha")
    plt.ylabel("Equity (base 1.0)")
    plt.grid(True, alpha=0.3)
    plt.legend(ncol=2)
    plt.tight_layout()
    ts = datetime.utcnow().strftime("%Y%m%d")
    out = OUT_DIR / f"equity_multi_{ts}.png"
    plt.savefig(out, dpi=130)
    plt.close()
    print(f"Gráfico guardado en {out}")

if __name__ == "__main__":
    main()
