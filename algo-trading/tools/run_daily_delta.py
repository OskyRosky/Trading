from pathlib import Path
import subprocess, yaml

CFG = Path("configs/symbols.yml")
syms = list(yaml.safe_load(CFG.read_text())["symbol_map"].keys())

ok = True
for s in syms:
    print(f"=== Delta {s} ===")
    try:
        subprocess.run(
            ["python", "-m", "services.ingestion.pipeline", "delta", s],
            check=True
        )
    except subprocess.CalledProcessError as e:
        ok = False
        print(f"[ERROR] {s}: {e}")

if not ok:
    raise SystemExit(1)
