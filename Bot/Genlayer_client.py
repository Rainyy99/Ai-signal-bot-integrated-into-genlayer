import asyncio
import aiohttp
import json
import os
from typing import Optional
from colorama import Fore, Style

class GenLayerClient:
    def __init__(self, rpc_url, contract_address, private_key):
        self.rpc_url          = rpc_url.rstrip("/")
        self.contract_address = contract_address
        self.private_key      = private_key
        self._req_id          = 0

    def _next_id(self):
        self._req_id += 1
        return self._req_id

    def _encode(self, method, **kwargs):
        data = json.dumps({"method": method, "args": kwargs})
        return "0x" + data.encode().hex()

    def _decode(self, hex_data):
        try:
            clean = hex_data.replace("0x", "")
            if len(clean) < 128:
                return None
            return bytes.fromhex(
                clean[128:]
            ).rstrip(b"\x00").decode("utf-8")
        except Exception:
            return None

    async def send_signal(self, signal):
        reasons_str = " | ".join(signal.reasons)
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "eth_sendTransaction",
            "params": [{
                "from": os.getenv("WALLET_ADDRESS", ""),
                "to":   self.contract_address,
                "data": self._encode(
                    "validate_and_store_signal",
                    pair=signal.coin,
                    action=signal.action,
                    strength=signal.strength,
                    price=signal.price,
                    rsi=signal.rsi,
                    macd=signal.macd,
                    ema_trend=signal.ema_trend,
                    reasons=reasons_str,
                    tp1=signal.tp1,
                    tp2=signal.tp2,
                    sl=signal.sl_tight,
                    rr_ratio=signal.rr_ratio,
                    timeframe=signal.timeframe,
                ),
                "gas": "0x100000",
            }]
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    self.rpc_url, json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as r:
                    result = await r.json()
                    tx = result.get("result")
                    if tx:
                        print(
                            f"{Fore.CYAN}TX sent: {tx}{Style.RESET_ALL}"
                        )
                        return {"tx_hash": tx}
                    print(
                        f"{Fore.RED}TX failed: "
                        f"{result.get('error')}{Style.RESET_ALL}"
                    )
                    return None
        except Exception as e:
            print(f"{Fore.RED}GenLayer error: {e}{Style.RESET_ALL}")
            return None

    async def get_last_signal(self):
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "eth_call",
            "params": [{
                "to":   self.contract_address,
                "data": self._encode("get_last_signal"),
            }, "latest"]
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    self.rpc_url, json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as r:
                    result = await r.json()
                    raw = result.get("result", "")
                    if raw and raw != "0x":
                        decoded = self._decode(raw)
                        if decoded:
                            return json.loads(decoded)
            return None
        except Exception as e:
            print(f"{Fore.RED}GenLayer read error: {e}{Style.RESET_ALL}")
            return None

    async def wait_for_consensus(self, tx_hash, max_wait=120):
        print(
            f"{Fore.YELLOW}Menunggu LLM validators...{Style.RESET_ALL}"
        )
        waited = 0
        while waited < max_wait:
            await asyncio.sleep(5)
            waited += 5
            result = await self.get_last_signal()
            if result:
                print(
                    f"{Fore.GREEN}Konsensus! "
                    f"({waited}s){Style.RESET_ALL}"
                )
                return result
            print(f"  Menunggu... ({waited}s)")
        print(f"{Fore.RED}Timeout konsensus{Style.RESET_ALL}")
        return None
