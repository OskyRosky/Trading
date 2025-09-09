import yaml, pathlib

def test_configs_exist_and_symbols_loaded():
    base = pathlib.Path(__file__).resolve().parents[1]
    for rel in ["configs/symbols.yml", "configs/data_paths.yml", "configs/orchestration.yml"]:
        assert (base / rel).exists(), f"Missing {rel}"

    with open(base / "configs/symbols.yml", "r") as f:
        cfg = yaml.safe_load(f)
    smap = cfg.get("symbol_map", {})
    assert len(smap) == 19, f"Expected 19 mapped symbols, got {len(smap)}"

    # Normalización de sufijos .P
    assert smap["1000SHIBUSDT.P"] == "1000SHIBUSDT"
    assert smap["XMRUSDT.P"] == "XMRUSDT"

def test_paths_point_to_user_data():
    base = pathlib.Path(__file__).resolve().parents[1]
    dp = yaml.safe_load((base / "configs" / "data_paths.yml").read_text())
    assert dp["data_root"] == "/Users/sultan/Trading/data"
    assert dp["checkpoints_dir"].startswith(dp["data_root"])
    assert dp["trusted_root"].startswith(dp["data_root"])
    assert dp["curated_root"].startswith(dp["data_root"])