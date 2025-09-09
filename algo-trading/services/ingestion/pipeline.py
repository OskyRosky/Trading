from __future__ import annotations
import json
from pathlib import Path
import yaml, pandas as pd, typer
from services.ingestion.binance_client import paginate_klines_1d
from services.processing.validate import normalize_klines_to_df, validate_ohlcv_rules
from services.ingestion.writer import save_checkpoint, load_checkpoint, upsert_parquet_curated

app = typer.Typer(help="Ingesta OHLCV 1d Futuros USDT-M (PERP) → Parquet")

def _load_cfg() -> tuple[dict, dict]:
    base = Path(__file__).resolve().parents[2]
    paths = yaml.safe_load((base/"configs"/"data_paths.yml").read_text())
    symbols = yaml.safe_load((base/"configs"/"symbols.yml").read_text())
    return paths, symbols

def _ckpt_path(paths:dict, symbol:str) -> str:
    return str(Path(paths["checkpoints_dir"]) / f"{symbol}_1d_klines.json")

@app.command()
def backfill(symbol: str, start: str="2017-08-17", end: str=None):
    paths, symbols = _load_cfg()
    api_symbol = symbols["symbol_map"].get(symbol, symbol)
    market = symbols.get("market","futures")
    segment = symbols.get("segment","usdtm")
    contract = symbols.get("contract","perpetual")
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp()*1000)
    end_ms = int(pd.Timestamp(end, tz="UTC").timestamp()*1000) if end else int(pd.Timestamp.utcnow().timestamp()*1000)

    ckpt_file = _ckpt_path(paths, symbol)
    last = load_checkpoint(ckpt_file)
    if last is not None and last > start_ms:
        start_ms = last + 1

    total_rows = 0
    last_close_ms = None
    for batch in paginate_klines_1d(api_symbol, start_ms, end_ms):
        df = normalize_klines_to_df(batch)
        df = validate_ohlcv_rules(df)
        if df.empty:
            continue
        upsert_parquet_curated(df, paths["curated_root"], market, segment, contract, symbol, "1d")
        total_rows += len(df)
        last_close_ms = int(df["close_time"].iloc[-1])
        save_checkpoint(ckpt_file, last_close_ms)

    typer.echo(json.dumps({"symbol": symbol, "rows_written": total_rows, "last_close_time": last_close_ms}, indent=2))

@app.command()
def delta(symbol: str):
    return backfill(symbol=symbol, start="1970-01-01", end=None)

if __name__ == "__main__":
    app()
