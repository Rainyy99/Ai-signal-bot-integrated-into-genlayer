import aiohttp
import asyncio
import pandas as pd
import time
from typing import Optional
from colorama import Fore, Style

HL_URL = "https://api.hyperliquid.xyz/info"

INTERVAL_MS = {
    "1m": 60000, "3m": 180000, "5m": 300000,
    "15m": 900000, "30m": 1800000,
    "1h": 3600000, "4h": 14400000, "1d": 86400000,
}

class HyperliquidFetcher:
    def __init__(self):
        print(f"{Fore.GREEN}Hyperliquid API siap (no API key){Style.RESET_ALL}")

    async def fetch_ohlcv(self, coin, interval="15m", limit=300):
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
                    HL_URL, json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    data = await resp.json()
                    if not data or len(data) < 50:
                        return None
                    df = pd.DataFrame(data)
                    df = df.rename(columns={
                        "t": "timestamp", "o": "open",
                        "h": "high", "l": "low",
                        "c": "close", "v": "volume",
                    })
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                    df.set_index("timestamp", inplace=True)
                    for col in ["open","high","low","close","volume"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    return df.dropna()
        except Exception as e:
            print(f"{Fore.RED}Fetch error {coin}: {e}{Style.RESET_ALL}")
            return None

    async def fetch_funding_rate(self, coin):
        payload = {"type": "metaAndAssetCtxs"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    HL_URL, json=payload,
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

    async def fetch_open_interest(self, coin):
        payload = {"type": "metaAndAssetCtxs"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    HL_URL, json=payload,
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

    async def fetch_mark_price(self, coin):
        payload = {"type": "allMids"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    HL_URL, json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    data = await resp.json()
                    return float(data.get(coin, 0)) or None
        except Exception:
            return None
