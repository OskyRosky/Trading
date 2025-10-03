import sys, pathlib, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.ml.utils import load_cfg

def test_supervised_outputs_exist_and_valid():
    paths, symbols, ml_cfg = load_cfg()
    base = pathlib.Path("/Users/sultan/Trading/data/ml/datasets")
    assert (base/"all_1d.parquet").exists(), "Falta combinado all_1d.parquet"
    df = pd.read_parquet(base/"all_1d.parquet")
    required = {"date","symbol","close","ret_fwd_1d","y_up"}
    assert required.issubset(df.columns), f"Columnas faltantes: {required - set(df.columns)}"
    assert df["date"].is_monotonic_increasing is False, "Combinado puede mezclar símbolos; validaremos por símbolo"
    for sym in symbols["symbol_map"].keys():
        part = df[df["symbol"]==sym].sort_values("date")
        if len(part)==0:
            continue
        assert part["date"].is_monotonic_increasing, f"Fechas no monótonas en {sym}"
        assert part["date"].duplicated().sum()==0, f"Duplicados de fecha en {sym}"
        assert part["y_up"].dropna().isin([0,1]).all(), f"y_up inválido en {sym}"
        assert part["ret_fwd_1d"].notna().all(), f"ret_fwd_1d con NaN en {sym}"
