import asyncio
from datetime import datetime
from typing import List, Optional
from colorama import Fore, Style, init
from .analyzer import TechnicalAnalyzer, Signal
from .fetcher import HyperliquidFetcher
init(autoreset=True)

class TradingAgent:
    def __init__(self, config):
        self.coins            = [c.strip() for c in config.get("coins","BTC").split(",")]
        self.timeframe        = config.get("timeframe","15m")
        self.scan_interval    = int(config.get("scan_interval",60))
        self.min_strength     = float(config.get("min_signal_strength",65))
        self.use_genlayer     = config.get("use_genlayer","false").lower() == "true"
        self.contract_address = config.get("genlayer_contract_address","")
        self.fetcher          = HyperliquidFetcher()
        self.analyzer         = TechnicalAnalyzer()
        self.genlayer         = None
        if self.use_genlayer and self.contract_address:
            from .genlayer_client import GenLayerClient
            self.genlayer = GenLayerClient(
                rpc_url=config.get("genlayer_rpc_url","https://rpc.asimov.genlayer.com"),
                contract_address=self.contract_address,
                private_key=config.get("wallet_private_key",""),
            )
        self.bot       = None
        self._start    = datetime.now()
        self._scans    = 0
        self._sent     = 0
        self._validated= 0
        self._last     = "Belum pernah"
        self._running  = False

    def set_bot(self, bot):
        self.bot = bot

    async def run(self):
        self._running = True
        print(f"\n{'='*50}")
        print(f"  HL SIGNAL BOT + GENLAYER")
        print(f"  Coins    : {', '.join(self.coins)}")
        print(f"  TF       : {self.timeframe}")
        print(f"  GenLayer : {'ON' if self.use_genlayer else 'OFF'}")
        print(f"{'='*50}\n")
        while self._running:
            try:
                await self._scan_all()
                print(f"Menunggu {self.scan_interval}s...")
                await asyncio.sleep(self.scan_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Loop error: {e}")
                await asyncio.sleep(10)

    async def _scan_all(self):
        self._scans += 1
        self._last = datetime.now().strftime("%H:%M:%S")
        print(f"\nScan #{self._scans} — {self._last}")
        for coin in self.coins:
            await self.scan_and_send_single(coin)
            await asyncio.sleep(2)

    async def scan_and_send_single(self, coin):
        signal = await self._scan_single(coin)
        if not signal:
            print(f"  {coin}: data error")
            return
        print(f"  {coin}: {signal.action} {signal.strength}%", end="")
        if signal.strength < self.min_strength:
            print(" (lemah)")
            return
        print(" SINYAL!")
        self._sent += 1
        if self.use_genlayer and self.genlayer:
            if self.bot:
                await self.bot.send_pending_signal(signal)
            tx = await self.genlayer.send_signal(signal)
            if tx:
                consensus = await self.genlayer.wait_for_consensus(tx["tx_hash"])
                if consensus and self.bot:
                    await self.bot.send_validated_signal(signal, consensus)
                    self._validated += 1
        else:
            if self.bot:
                await self.bot.send_pending_signal(signal)

    async def _scan_single(self, coin):
        try:
            df = await self.fetcher.fetch_ohlcv(coin, self.timeframe, 300)
            if df is None:
                return None
            sig = self.analyzer.analyze(coin, df, self.timeframe)
            if sig:
                sig.funding_rate  = await self.fetcher.fetch_funding_rate(coin)
                sig.open_interest = await self.fetcher.fetch_open_interest(coin)
            return sig
        except Exception as e:
            print(f"Scan error {coin}: {e}")
            return None

    async def manual_scan(self):
        results = []
        for coin in self.coins:
            sig = await self._scan_single(coin)
            if sig and sig.strength >= self.min_strength:
                results.append(sig)
                await self.scan_and_send_single(coin)
        return results

    def get_status(self):
        up = datetime.now() - self._start
        h, r = divmod(int(up.total_seconds()), 3600)
        m, s = divmod(
