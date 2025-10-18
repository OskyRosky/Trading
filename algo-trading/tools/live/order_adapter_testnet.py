from __future__ import annotations
import os, time, hmac, hashlib
import json
from urllib.parse import urlencode
import requests

TESTNET_BASE = "https://testnet.binancefuture.com"  # Binance USDⓈ-M Futures Testnet

class BinanceUSDMTestnet:
    def __init__(self, api_key: str, api_secret: str, dry_run: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8") if api_secret else b""
        self.dry_run = dry_run

    def _headers(self):
        return {"X-MBX-APIKEY": self.api_key}

    def _sign(self, params: dict) -> str:
        qs = urlencode(params)
        sig = hmac.new(self.api_secret, qs.encode("utf-8"), hashlib.sha256).hexdigest()
        return qs + "&signature=" + sig

    def market_order(self, symbol: str, side: str, quantity: float) -> dict:
        """
        Crea orden de mercado en Testnet (si dry_run=False).
        Devuelve dict con info básica (simulada o real).
        """
        if self.dry_run:
            # Simula respuesta (no pega a la API)
            return {
                "status": "SIMULATED",
                "symbol": symbol,
                "side": side.upper(),
                "executedQty": quantity,
                "price": None,
                "orderId": f"SIM-{int(time.time()*1000)}",
            }

        endpoint = "/fapi/v1/order"
        url = TESTNET_BASE + endpoint
        ts = int(time.time() * 1000)
        payload = {
            "symbol": symbol,
            "side": side.upper(),          # BUY / SELL
            "type": "MARKET",
            "quantity": quantity,
            "timestamp": ts,
            "recvWindow": 5000,
        }
        qs = self._sign(payload)
        r = requests.post(url, headers=self._headers(), data=qs, timeout=10)
        r.raise_for_status()
        return r.json()

def from_env() -> BinanceUSDMTestnet:
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    dry = os.getenv("ENABLE_TESTNET", "0") != "1"
    return BinanceUSDMTestnet(api_key, api_secret, dry_run=dry)
