import importlib

deps = [
    "pandas",
    "pyyaml",
    "httpx",
    "tenacity",
    "duckdb",
    "tabulate",
    "typer",
    "joblib",
    "sklearn",
    "matplotlib",
]

print("🔍 Verificando dependencias...\n")
for dep in deps:
    try:
        importlib.import_module(dep)
        print(f"[OK] {dep}")
    except ImportError:
        print(f"[MISSING] {dep} -> instalar con: pip install {dep}")
