from pathlib import Path
import subprocess, yaml, sys

BASE = Path(__file__).resolve().parents[1]
CFG = BASE / "configs" / "symbols.yml"

def main():
    cfg = yaml.safe_load(CFG.read_text())
    syms = list(cfg["symbol_map"].keys())
    ok = True
    for s in syms:
        print(f"[features] {s}")
        try:
            subprocess.run(
                [sys.executable, "-m", "services.features.features_pipeline", "--symbol", s],
                check=True
            )
        except subprocess.CalledProcessError as e:
            ok = False
            print(f"[ERROR] {s}: {e}")
    if not ok:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
