import asyncio
import json
import time
from typing import Optional
from colorama import Fore, Style

from genlayer_py import create_client, create_account
from genlayer_py.chains import studionet
from genlayer_py.types import TransactionStatus, ExecutionResult


class GenLayerClient:
    def __init__(self, contract_address: str, private_key: str = ""):
        self.contract_address = contract_address

        if private_key:
            clean_key = private_key[2:] if private_key.startswith("0x") else private_key
            key_bytes = bytes.fromhex(clean_key)
            self.account = create_account(key_bytes)
        else:
            self.account = create_account()
            print(
                Fore.YELLOW +
                "PERINGATAN: Tidak ada WALLET_PRIVATE_KEY di .env — "
                "akun baru dibuat otomatis:\n"
                "  Address    : " + self.account.address + "\n"
                "  Private Key: " + self.account.key.hex() + "\n"
                "Simpan private key ini ke .env sebagai WALLET_PRIVATE_KEY "
                "dan fund akun ini via faucet sebelum lanjut." +
                Style.RESET_ALL
            )

        self.client = create_client(chain=studionet, account=self.account)
        print(
            Fore.GREEN +
            "GenLayer client (genlayer-py SDK) siap. Account: " +
            self.account.address + Style.RESET_ALL
        )

    def _make_signal_id(self, coin: str) -> str:
        return coin + "_" + str(int(time.time() * 1000))

    async def send_signal(self, signal):
        loop = asyncio.get_event_loop()
        signal_id = self._make_signal_id(signal.coin)
        reasons_str = " | ".join(signal.reasons)

        args = [
            signal_id,
            signal.coin,
            signal.action,
            str(signal.strength),
            str(signal.price),
            str(signal.rsi),
            str(signal.macd),
            signal.ema_trend,
            reasons_str,
            str(signal.tp1),
            str(signal.tp2),
            str(signal.sl_tight),
            str(signal.rr_ratio),
            signal.timeframe,
        ]

        def _write():
            return self.client.write_contract(
                account=self.account,
                address=self.contract_address,
                function_name="validate_and_store_signal",
                args=args,
                value=0,
            )

        try:
            tx_hash = await loop.run_in_executor(None, _write)
            print(
                Fore.CYAN + "TX sent: " + str(tx_hash) +
                " | signal_id: " + signal_id + Style.RESET_ALL
            )
            return {"tx_hash": tx_hash, "signal_id": signal_id}
        except Exception as e:
            print(Fore.RED + "GenLayer send error: " + str(e) + Style.RESET_ALL)
            return None

    async def wait_for_consensus(self, tx_hash: str, signal_id: str, max_wait: int = 180):
        loop = asyncio.get_event_loop()
        print(
            Fore.YELLOW + "Menunggu finalisasi transaksi " +
            str(tx_hash) + "..." + Style.RESET_ALL
        )

        def _wait_receipt():
            return self.client.wait_for_transaction_receipt(
                transaction_hash=tx_hash,
                status=TransactionStatus.FINALIZED,
            )

        try:
            receipt = await loop.run_in_executor(None, _wait_receipt)
        except Exception as e:
            print(Fore.RED + "Receipt error: " + str(e) + Style.RESET_ALL)
            return None

        result_name = receipt.get("tx_execution_result_name")
        if result_name == ExecutionResult.FINISHED_WITH_ERROR.value:
            print(Fore.RED + "Eksekusi contract GAGAL untuk TX ini." + Style.RESET_ALL)
            return None
        if result_name != ExecutionResult.FINISHED_WITH_RETURN.value:
            print(Fore.RED + "Eksekusi belum selesai/voted: " + str(result_name) + Style.RESET_ALL)
            return None

        def _read():
            return self.client.read_contract(
                address=self.contract_address,
                function_name="get_signal",
                args=[signal_id],
            )

        try:
            raw = await loop.run_in_executor(None, _read)
        except Exception as e:
            print(Fore.RED + "Read error: " + str(e) + Style.RESET_ALL)
            return None

        if not raw:
            print(Fore.RED + "signal_id tidak ditemukan di contract." + Style.RESET_ALL)
            return None

        print(Fore.GREEN + "Konsensus selesai & terverifikasi on-chain!" + Style.RESET_ALL)
        return json.loads(raw)

    async def get_last_signal(self):
        loop = asyncio.get_event_loop()

        def _read():
            return self.client.read_contract(
                address=self.contract_address,
                function_name="get_last_signal",
                args=[],
            )

        try:
            raw = await loop.run_in_executor(None, _read)
            return json.loads(raw) if raw else None
        except Exception as e:
            print(Fore.RED + "Read last_signal error: " + str(e) + Style.RESET_ALL)
            return None

    async def get_stats(self):
        loop = asyncio.get_event_loop()

        def _read():
            return self.client.read_contract(
                address=self.contract_address,
                function_name="get_stats",
                args=[],
            )

        try:
            raw = await loop.run_in_executor(None, _read)
            return json.loads(raw) if raw else None
        except Exception as e:
            print(Fore.RED + "Read stats error: " + str(e) + Style.RESET_ALL)
            return None