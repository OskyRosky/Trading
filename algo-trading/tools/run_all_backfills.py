from pathlib import Path
import subprocess, yaml

cfg = yaml.safe_load(Path("configs/symbols.yml").read_text())
syms = list(cfg["symbol_map"].keys())

for s in syms:
    print(f"=== Backfill {s} ===")
    try:
        subprocess.run(
            ["python", "-m", "services.ingestion.pipeline", "backfill", s],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error en {s}: {e}")
