import aiohttp
import time
from typing import Optional, List, Dict
from colorama import Fore, Style

HL_URL = "https://api.hyperliquid.xyz/info"

INTERVAL_MS = {
    "1m":  60000,
    "5m":  300000,
    "15m": 900000,
    "30m": 1800000,
    "1h":  3600000,
    "4h":  14400000,
    "1d":  86400000,
}


class HyperliquidFetcher:
    def __init__(self):
        print(Fore.GREEN + "Hyperliquid API siap (tanpa API key, tanpa pandas)" + Style.RESET_ALL)

    async def fetch_ohlcv(self, coin: str, interval: str = "15m", limit: int = 300):
        interval_ms = INTERVAL_MS.get(interval, 900000)
        end_time    = int(time.time() * 1000)
        start_time  = end_time - (interval_ms * limit)
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin":      coin,
                "interval":  interval,
                "startTime": start_time,
                "endTime":   end_time,
            }
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    HL_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    data = await resp.json()
                    if not data or len(data) < 50:
                        return None

                    candles = []
                    for c in data:
                        candles.append({
                            "timestamp": int(c["t"]),
                            "open":      float(c["o"]),
                            "high":      float(c["h"]),
                            "low":       float(c["l"]),
                            "close":     float(c["c"]),
                            "volume":    float(c["v"]),
                        })
                    candles.sort(key=lambda x: x["timestamp"])
                    return candles
        except Exception as e:
            print(Fore.RED + "Fetch error " + coin + ": " + str(e) + Style.RESET_ALL)
            return None

    async def fetch_funding_rate(self, coin: str):
        payload = {"type": "metaAndAssetCtxs"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    HL_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    data = await resp.json()
                    meta     = data[0]["universe"]
                    contexts = data[1]
                    for i, asset in enumerate(meta):
                        if asset["name"] == coin:
                            fr = float(contexts[i].get("funding", 0))
                            return round(fr * 100, 6)
            return None
        except Exception:
            return None

    async def fetch_open_interest(self, coin: str):
        payload = {"type": "metaAndAssetCtxs"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    HL_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    data = await resp.json()
                    meta     = data[0]["universe"]
                    contexts = data[1]
                    for i, asset in enumerate(meta):
                        if asset["name"] == coin:
                            return float(contexts[i].get("openInterest", 0))
            return None
        except Exception:
            return None