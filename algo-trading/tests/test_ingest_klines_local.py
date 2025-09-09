import pandas as pd
from services.processing.validate import validate_ohlcv_rules

def test_validate_basic_rules():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01","2024-01-02"], utc=True),
        "open":[100,110],"high":[120,130],"low":[90,100],"close":[115,120],
        "volume":[10,20],"trades":[100,200],"quote_volume":[1000,2000],"close_time":[1704067200000,1704153600000]
    })
    out = validate_ohlcv_rules(df)
    assert len(out)==2
