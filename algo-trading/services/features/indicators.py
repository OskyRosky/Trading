from __future__ import annotations
import pandas as pd
import numpy as np

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.clip(lower=0)).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr14 = tr.rolling(period).mean()
    pdi = 100 * (pd.Series(plus_dm, index=high.index).rolling(period).sum() / atr14)
    mdi = 100 * (pd.Series(minus_dm, index=high.index).rolling(period).sum() / atr14)
    dx = (abs(pdi - mdi) / (pdi + mdi).replace(0, np.nan)) * 100
    return dx.rolling(period).mean()

def bollinger(close: pd.Series, period: int = 20, k: float = 2.0):
    ma = close.rolling(period).mean()
    sd = close.rolling(period).std(ddof=0)
    upper = ma + k * sd
    lower = ma - k * sd
    return ma, upper, lower

def basic_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret_pct"] = out["close"].pct_change()
    out["ret_log"] = np.log(out["close"] / out["close"].shift(1))
    out["sma_7"]   = out["close"].rolling(7).mean()
    out["sma_20"]  = out["close"].rolling(20).mean()
    out["ema_12"]  = _ema(out["close"], 12)
    out["ema_26"]  = _ema(out["close"], 26)
    out["rsi_14"]  = rsi(out["close"], 14)
    out["atr_14"]  = atr(out["high"], out["low"], out["close"], 14)
    out["adx_14"]  = adx(out["high"], out["low"], out["close"], 14)
    bb_ma, bb_u, bb_l = bollinger(out["close"], 20, 2.0)
    out["bb_ma_20_2"] = bb_ma
    out["bb_u_20_2"]  = bb_u
    out["bb_l_20_2"]  = bb_l
    cols = [
        "date","open","high","low","close","volume","trades","quote_volume","close_time",
        "ret_pct","ret_log","sma_7","sma_20","ema_12","ema_26","rsi_14","atr_14","adx_14",
        "bb_ma_20_2","bb_u_20_2","bb_l_20_2"
    ]
    out = out[cols]
    return out
