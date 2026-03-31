import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv("config/.env")

def check():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    cid   = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or "ISI" in token:
        print("ERROR: Set TELEGRAM_BOT_TOKEN di config/.env")
        sys.exit(1)
    if not cid or "ISI" in cid:
        print("ERROR: Set TELEGRAM_CHAT_ID di config/.env")
        sys.exit(1)
    return {
        "coins":                     os.getenv("COINS", "BTC,ETH,SOL"),
        "timeframe":                 os.getenv("TIMEFRAME", "15m"),
        "scan_interval":             os.getenv("SCAN_INTERVAL", "60"),
        "min_signal_strength":       os.getenv(
            "MIN_SIGNAL_STRENGTH", "65"
        ),
        "use_genlayer":              os.getenv("USE_GENLAYER", "false"),
        "genlayer_rpc_url":          os.getenv("GENLAYER_RPC_URL", ""),
        "genlayer_contract_address": os.getenv(
            "GENLAYER_CONTRACT_ADDRESS", ""
        ),
        "wallet_address":            os.getenv("WALLET_ADDRESS", ""),
        "wallet_private_key":        os.getenv("WALLET_PRIVATE_KEY", ""),
        "telegram_token":            token,
        "telegram_chat_id":          cid,
    }

async def main():
    print("=== HL SIGNAL BOT + GENLAYER ===")
    cfg = check()
    from bot.agent import TradingAgent
    from bot.telegram_bot import TelegramBot
    agent = TradingAgent(cfg)
    bot   = TelegramBot(
        cfg["telegram_token"], cfg["telegram_chat_id"], agent
    )
    agent.set_bot(bot)
    await bot.setup()
    try:
        await agent.run()
    except KeyboardInterrupt:
        print("Bot dihentikan")
    finally:
        agent.stop()
        await bot.send_msg("Bot dimatikan.")
        await bot.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Berhenti.")
