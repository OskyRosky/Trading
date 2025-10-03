from __future__ import annotations
import argparse, pathlib, datetime
import duckdb, yaml, pandas as pd
import matplotlib.pyplot as plt

BASE = pathlib.Path("/Users/sultan/Trading/algo-trading")
DATA_ROOT = pathlib.Path("/Users/sultan/Trading/data")
FIG_DIR = DATA_ROOT / "checks" / "figures"
OUT_DIR = DATA_ROOT / "checks" / "reports"
FIG_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_cfg():
    paths = yaml.safe_load((BASE/"configs"/"data_paths.yml").read_text())
    return paths

def read_trusted(symbol: str, rows: int) -> pd.DataFrame:
    paths = load_cfg()
    pat = f"{paths['trusted_root']}/market=futures/segment=usdtm/contract=perpetual/symbol={symbol}/interval=1d/**/data.parquet"
    con = duckdb.connect()
    df = con.execute(f"""
      SELECT * FROM read_parquet('{pat}', hive_partitioning=1)
      ORDER BY date DESC
      LIMIT {rows}
    """).fetchdf()
    df = df.sort_values("date").reset_index(drop=True)
    return df

def quick_checks(df: pd.DataFrame) -> dict:
    out = {}
    out["rows"] = len(df)
    out["nulls_rsi"] = int(df["rsi_14"].isna().sum()) if "rsi_14" in df else None
    out["rsi_min"] = float(df["rsi_14"].min()) if "rsi_14" in df else None
    out["rsi_max"] = float(df["rsi_14"].max()) if "rsi_14" in df else None
    out["atr_median"] = float(df["atr_14"].median()) if "atr_14" in df else None
    out["sma7_nulls"] = int(df["sma_7"].isna().sum()) if "sma_7" in df else None
    out["sma20_nulls"] = int(df["sma_20"].isna().sum()) if "sma_20" in df else None

    # flags de alerta simples
    flags = []
    if out["rsi_min"] is not None and (out["rsi_min"] < -1 or out["rsi_min"] > 101):
        flags.append("RSI fuera de rango inferior/superior")
    if out["rsi_max"] is not None and (out["rsi_max"] < -1 or out["rsi_max"] > 101):
        flags.append("RSI fuera de rango inferior/superior")
    if out["atr_median"] is not None and out["atr_median"] <= 0:
        flags.append("ATR mediana <= 0")
    out["flags"] = flags
    return out

def plot_symbol(df: pd.DataFrame, symbol: str) -> pathlib.Path:
    ts = datetime.datetime.utcnow().strftime("%Y%m%d")
    figpath = FIG_DIR / f"{symbol}_sanity_{ts}.png"

    # Figura 1: close + sma7 + sma20
    plt.figure(figsize=(11,5))
    plt.plot(df["date"], df["close"], label="close")
    if "sma_7" in df:  plt.plot(df["date"], df["sma_7"], label="sma_7")
    if "sma_20" in df: plt.plot(df["date"], df["sma_20"], label="sma_20")
    plt.title(f"{symbol} — Close vs SMA(7,20)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figpath, dpi=130)
    plt.close()

    # Figura 2: RSI
    if "rsi_14" in df:
        figpath_rsi = FIG_DIR / f"{symbol}_rsi_{ts}.png"
        plt.figure(figsize=(11,3))
        plt.plot(df["date"], df["rsi_14"], label="rsi_14")
        plt.axhline(30, linestyle="--")
        plt.axhline(70, linestyle="--")
        plt.title(f"{symbol} — RSI(14)")
        plt.tight_layout()
        plt.savefig(figpath_rsi, dpi=130)
        plt.close()

    # Figura 3: ATR
    if "atr_14" in df:
        figpath_atr = FIG_DIR / f"{symbol}_atr_{ts}.png"
        plt.figure(figsize=(11,3))
        plt.plot(df["date"], df["atr_14"], label="atr_14")
        plt.title(f"{symbol} — ATR(14)")
        plt.tight_layout()
        plt.savefig(figpath_atr, dpi=130)
        plt.close()

    return figpath

def save_snapshot(df: pd.DataFrame, symbol: str) -> pathlib.Path:
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    snap = OUT_DIR / f"features_snapshot_{symbol}_{ts}.csv"
    cols = [c for c in ["date","close","sma_7","sma_20","ema_12","ema_26","rsi_14","atr_14","volume","trades"] if c in df.columns]
    df[cols].to_csv(snap, index=False)
    return snap

def main():
    p = argparse.ArgumentParser(description="Sanity check de features (trusted)")
    p.add_argument("--symbol", required=True, help="Símbolo, p.ej. BTCUSDT")
    p.add_argument("--rows", type=int, default=300, help="Últimas N filas a inspeccionar")
    args = p.parse_args()

    df = read_trusted(args.symbol, args.rows)
    if df.empty:
        print(f"[WARN] Sin datos trusted para {args.symbol}")
        return

    checks = quick_checks(df)
    print("Sanity:", checks)
    fig = plot_symbol(df, args.symbol)
    csv = save_snapshot(df, args.symbol)
    print("Gráficas en:", FIG_DIR)
    print("Snapshot CSV:", csv)

if __name__ == "__main__":
    main()
