from __future__ import annotations
from pathlib import Path
import subprocess, yaml, sys, csv

BASE = Path(__file__).resolve().parents[1]
CFG = BASE / "configs" / "symbols.yml"
OUT = Path("/Users/sultan/Trading/data/checks/reports/backtest_metrics.csv")

def main():
    cfg = yaml.safe_load(CFG.read_text())
    syms = list(cfg["symbol_map"].keys())
    rows = []
    for s in syms:
        print(f"[BT] {s}")
        try:
            r = subprocess.run(
                [sys.executable, "tools/backtest_sma.py", "--symbol", s, "--start", "2020-01-01", "--fee_bps", "2.0", "--no_rsi"],
                capture_output=True, text=True, check=True
            )
            line = next((ln for ln in r.stdout.splitlines() if ln.startswith("Metrics ")), None)
            # ej: Metrics BTCUSDT:  {'CAGR': 0.4368, 'Sharpe': np.float64(0.8649), 'MaxDD': -0.7284}
            if line:
                num = {}
                seg = line.split("{",1)[1].rstrip("}")
                for kv in seg.split(","):
                    k, v = kv.strip().split(":")
                    k = k.strip().strip("'").strip('"')
                    v = v.strip()
                    v = v.replace("np.float64(","").replace(")","")
                    num[k] = float(v)
                rows.append({"symbol": s, "CAGR": num.get("CAGR"), "Sharpe": num.get("Sharpe"), "MaxDD": num.get("MaxDD")})
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] {s}: {e}\n{e.stdout}\n{e.stderr}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["symbol","CAGR","Sharpe","MaxDD"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Métricas guardadas en {OUT}")

if __name__ == "__main__":
    main()
