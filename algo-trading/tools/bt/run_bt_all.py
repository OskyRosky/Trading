from __future__ import annotations
from pathlib import Path
import subprocess, yaml

BASE = Path("/Users/sultan/Trading/algo-trading")
CFG = BASE/"configs"/"symbols.yml"

cfg = yaml.safe_load(CFG.read_text())
syms = list(cfg["symbol_map"].keys())

for s in syms:
    try:
        subprocess.run(
            ["python", "tools/bt/backtest_symbol_vs_hodl.py", "--symbol", s, "--fee_bps", "2.0"],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"BT error {s}: {e}")
