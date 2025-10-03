from __future__ import annotations
import argparse, pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import datetime

OUT_DIR = Path("/Users/sultan/Trading/data/checks/figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    p = argparse.ArgumentParser(description="Grafica equity curve desde CSV")
    p.add_argument("--csv", required=True, help="Ruta al CSV generado por backtest")
    args = p.parse_args()

    df = pd.read_csv(args.csv, parse_dates=["date"])
    if "equity" not in df.columns:
        raise SystemExit("CSV no tiene columna equity")

    ts = datetime.datetime.utcnow().strftime("%Y%m%d")
    figpath = OUT_DIR / f"equity_curve_{ts}.png"

    plt.figure(figsize=(11,5))
    plt.plot(df["date"], df["equity"], label="Equity curve", color="blue")
    plt.title("Evolución Equity Curve")
    plt.xlabel("Fecha")
    plt.ylabel("Equidad (base 1.0)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(figpath, dpi=130)
    plt.close()

    print(f"Gráfico guardado en {figpath}")

if __name__ == "__main__":
    main()
