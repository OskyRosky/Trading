from __future__ import annotations
import time
from typing import Iterable, List, Dict, Any, Optional
import httpx
from tenacity import retry, wait_exponential_jitter, stop_after_attempt, retry_if_exception_type

BINANCE_UF_BASE = "https://fapi.binance.com"  # USDT-M Futures

class BinanceRateLimit(Exception): ...
class BinanceHTTPError(Exception): ...

@retry(
    reraise=True,
    wait=wait_exponential_jitter(initial=1, max=60),
    stop=stop_after_attempt(7),
    retry=retry_if_exception_type((BinanceRateLimit, BinanceHTTPError, httpx.ConnectError, httpx.ReadTimeout))
)
def _get(path: str, params: Dict[str, Any]) -> Any:
    url = BINANCE_UF_BASE + path
    with httpx.Client(timeout=30) as client:
        r = client.get(url, params=params)
    if r.status_code == 429:
        raise BinanceRateLimit("HTTP 429 rate limit")
    if r.status_code >= 400:
        raise BinanceHTTPError(f"http {r.status_code}: {r.text[:200]}")
    return r.json()

def fetch_klines_1d(symbol: str, start_ms: Optional[int]=None, end_ms: Optional[int]=None, limit: int=1500) -> List[List[Any]]:
    params = {"symbol": symbol, "interval": "1d", "limit": limit}
    if start_ms is not None: params["startTime"] = start_ms
    if end_ms is not None: params["endTime"] = end_ms
    data = _get("/fapi/v1/klines", params)
    return data

def paginate_klines_1d(symbol: str, start_ms: int, end_ms: int, limit: int=1500) -> Iterable[List[List[Any]]]:
    current = start_ms
    while current <= end_ms:
        batch = fetch_klines_1d(symbol, start_ms=current, end_ms=end_ms, limit=limit)
        if not batch:
            break
        yield batch
        last_close = batch[-1][6]
        next_start = last_close + 1
        if next_start <= current:
            next_start = current + 1
        current = next_start
        time.sleep(0.2)
