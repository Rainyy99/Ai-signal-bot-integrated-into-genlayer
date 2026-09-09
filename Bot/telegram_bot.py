import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler,
    CallbackQueryHandler, ContextTypes
)
from telegram.constants import ParseMode
from colorama import Fore, Style

class TelegramBot:
    def __init__(self, token, chat_id, agent_ref):
        self.token   = token
        self.chat_id = str(chat_id)
        self.agent   = agent_ref
        self.app     = None
        self._sent   = set()

    async def setup(self):
        self.app = Application.builder().token(self.token).build()
        self.app.add_handler(
            CommandHandler("start",  self.cmd_start))
        self.app.add_handler(
            CommandHandler("help",   self.cmd_help))
        self.app.add_handler(
            CommandHandler("status", self.cmd_status))
        self.app.add_handler(
            CommandHandler("scan",   self.cmd_scan))
        self.app.add_handler(
            CommandHandler("coins",  self.cmd_coins))
        self.app.add_handler(
            CommandHandler("chain",  self.cmd_chain))
        self.app.add_handler(CallbackQueryHandler(self.on_callback))
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        print(f"{Fore.GREEN}Telegram Bot aktif!{Style.RESET_ALL}")
        gl_status = "ON" if self.agent.use_genlayer else "OFF"
        await self.send_msg(
            "*HL Signal Bot + GenLayer*\n"
            "Hyperliquid Perpetual DEX\n"
            "Coins: " + ", ".join(self.agent.coins) + "\n"
            "TF: " + self.agent.timeframe + "\n"
            "GenLayer: " + gl_status + "\n\n"
            "/help untuk perintah"
        )

    def pct(self, a, b):
        return round(abs(a - b) / b * 100, 2)

    def bar(self, strength):
        filled = int(strength / 10)
        return "".join(
            ["*" if i < filled else "." for i in range(10)]
        )

    async def send_pending_signal(self, signal):
        key = signal.coin + "_" + signal.action + "_" + str(
            round(signal.price, 2)
        )
        if key in self._sent:
            return
        self._sent.add(key)
        if len(self._sent) > 200:
            self._sent = set(list(self._sent)[-50:])

        now     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        reasons = ""
        for i, r in enumerate(signal.reasons):
            reasons += "   " + str(i + 1) + ". " + r + "\n"

        fr_line = ""
        if signal.funding_rate is not None:
            sign = "+" if signal.funding_rate > 0 else ""
            fr_line = (
                "\nFunding Rate: "
                + sign + str(signal.funding_rate) + "%"
            )

        oi_line = ""
        if signal.open_interest is not None:
            oi_line = (
                "\nOpen Interest: "
                + str(round(signal.open_interest, 0))
            )

        gl_line = ""
        if self.agent.use_genlayer:
            gl_line = "\n\nMengirim ke GenLayer untuk validasi LLM..."

        action_emoji = "LONG" if signal.action == "LONG" else "SHORT"
        header_emoji = "LONG" if signal.action == "LONG" else "SHORT"

        msg = (
            "*SINYAL " + header_emoji + "*\n"
            "------------------------\n"
            "PAIR     : " + signal.coin + "/USDC\n"
            "TIMEFRAME: " + signal.timeframe + "\n"
            "WAKTU    : " + now + "\n"
            "ENTRY    : " + str(signal.price) + fr_line + oi_line + "\n\n"
            "*TARGET PROFIT:*\n"
            "TP1: " + str(signal.tp1) +
            " (+" + str(self.pct(signal.tp1, signal.price)) + "%)\n"
            "TP2: " + str(signal.tp2) +
            " (+" + str(self.pct(signal.tp2, signal.price)) + "%)\n"
            "TP3: " + str(signal.tp3) +
            " (+" + str(self.pct(signal.tp3, signal.price)) + "%)\n\n"
            "*STOP LOSS:*\n"
            "SL Ketat : " + str(signal.sl_tight) +
            " (-" + str(self.pct(signal.sl_tight, signal.price)) + "%)\n"
            "SL Longgar: " + str(signal.sl_loose) +
            " (-" + str(self.pct(signal.sl_loose, signal.price)) + "%)\n\n"
            "*LEVERAGE:*\n"
            "Rekomendasi: " + str(signal.leverage_rec) + "x\n"
            "Maksimal   : " + str(signal.leverage_max) + "x\n"
            "Risiko/Trade: 1-3% modal\n\n"
            "*ANALISIS:*\n"
            "EMA Trend  : " + signal.ema_trend + "\n"
            "RSI        : " + str(signal.rsi) + "\n"
            "MACD       : " + str(signal.macd) + "\n"
            "BB Position: " + signal.bb_position + "\n"
            "ATR        : " + str(signal.atr) + "\n\n"
            "*ALASAN SINYAL:*\n" + reasons + "\n"
            "R/R RATIO: 1:" + str(signal.rr_ratio) + "\n"
            "STRENGTH : [" + self.bar(signal.strength) + "] " +
            str(signal.strength) + "%\n\n"
            "*MANAJEMEN POSISI:*\n"
            "- Ambil 50% posisi saat TP1\n"
            "- Geser SL ke breakeven setelah TP1\n"
            "- Biarkan sisa posisi ke TP2/TP3"
            + gl_line + "\n\n"
            "_DYOR. Bukan saran keuangan._"
        )
        await self.send_msg(msg)

    async def send_validated_signal(self, signal, consensus):
        validation = consensus.get("validation", "UNKNOWN")
        if validation != "VALID":
            await self.send_msg(
                "*SINYAL DITOLAK - LLM Validators*\n"
                "Pair: " + signal.coin + "/USDC\n"
                "Indikator tidak cukup konsisten\n"
                "untuk posisi " + signal.action + "\n\n"
                "_GenLayer Consensus: INVALID_"
            )
            return

        now     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        reasons = ""
        for i, r in enumerate(signal.reasons):
            reasons += "   " + str(i + 1) + ". " + r + "\n"

        fr_line = ""
        if signal.funding_rate is not None:
            sign = "+" if signal.funding_rate > 0 else ""
            fr_line = (
                "\nFunding Rate: "
                + sign + str(signal.funding_rate) + "%"
            )

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "Scan Ulang",
                callback_data="re_" + signal.coin
            ),
            InlineKeyboardButton(
                "On-Chain",
                callback_data="chain_" + signal.coin
            ),
        ]])

        msg = (
            "*SINYAL " + signal.action +
            " - TERVALIDASI ON-CHAIN*\n"
            "------------------------\n"
            "PAIR     : " + signal.coin + "/USDC\n"
            "TIMEFRAME: " + signal.timeframe + "\n"
            "WAKTU    : " + now + "\n"
            "ENTRY    : " + str(signal.price) + fr_line + "\n\n"
            "*TARGET PROFIT:*\n"
            "TP1: " + str(signal.tp1) +
            " (+" + str(self.pct(signal.tp1, signal.price)) + "%)\n"
            "TP2: " + str(signal.tp2) +
            " (+" + str(self.pct(signal.tp2, signal.price)) + "%)\n"
            "TP3: " + str(signal.tp3) +
            " (+" + str(self.pct(signal.tp3, signal.price)) + "%)\n\n"
            "*STOP LOSS:*\n"
            "SL Ketat : " + str(signal.sl_tight) +
            " (-" + str(self.pct(signal.sl_tight, signal.price)) + "%)\n"
            "SL Longgar: " + str(signal.sl_loose) +
            " (-" + str(self.pct(signal.sl_loose, signal.price)) + "%)\n\n"
            "LEVERAGE: " + str(signal.leverage_rec) + "x " +
            "(max " + str(signal.leverage_max) + "x)\n"
            "R/R     : 1:" + str(signal.rr_ratio) + "\n\n"
            "*ANALISIS:*\n"
            "EMA: " + signal.ema_trend +
            " | RSI: " + str(signal.rsi) + "\n"
            "MACD: " + str(signal.macd) +
            " | BB: " + signal.bb_position + "\n\n"
            "*ALASAN:*\n" + reasons + "\n"
            "STRENGTH: [" + self.bar(signal.strength) + "] " +
            str(signal.strength) + "%\n\n"
            "*GenLayer Consensus:*\n"
            "Status  : VALID\n"
            "Contract: " + self.agent.contract_address[:20] + "...\n\n"
            "- Ambil 50% di TP1\n"
            "- Geser SL ke BE setelah TP1\n"
            "- Biarkan sisa ke TP2/TP3\n\n"
            "_DYOR. Bukan saran keuangan._"
        )
        await self.send_msg(msg, kb)

    async def cmd_start(self, u, c):
        await u.message.reply_text(
            "HL Trading Signal Bot + GenLayer\n\n"
            "Sinyal perpetual Hyperliquid\n"
            "divalidasi on-chain oleh LLM validators.\n\n"
            "/help untuk perintah.",
            parse_mode=ParseMode.MARKDOWN
        )

    async def cmd_help(self, u, c):
        await u.message.reply_text(
            "*Perintah:*\n"
            "/status - Status bot\n"
            "/scan   - Scan manual\n"
            "/coins  - Daftar coins\n"
            "/chain  - Data on-chain\n"
            "/help   - Bantuan",
            parse_mode=ParseMode.MARKDOWN
        )

    async def cmd_status(self, u, c):
        st = self.agent.get_status()
        await u.message.reply_text(
            "*Status Bot*\n"
            "Exchange  : Hyperliquid\n"
            "Uptime    : " + st["uptime"] + "\n"
            "Scan      : " + str(st["total_scans"]) + "x\n"
            "Sinyal    : " + str(st["signals_sent"]) + "\n"
            "Validated : " + str(st["validated"]) + "\n"
            "Last scan : " + st["last_scan"],
            parse_mode=ParseMode.MARKDOWN
        )

    async def cmd_scan(self, u, c):
        await u.message.reply_text("Scanning Hyperliquid...")
        res = await self.agent.manual_scan()
        if res:
            await u.message.reply_text(
                str(len(res)) + " sinyal kuat ditemukan."
            )
        else:
            await u.message.reply_text(
                "Tidak ada sinyal kuat saat ini."
            )

    async def cmd_coins(self, u, c):
        text = "*Coins dipantau:*\n"
        for s in self.agent.coins:
            text += "  - " + s + "/USDC\n"
        await u.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_chain(self, u, c):
        data = None
        if self.agent.genlayer:
            data = await self.agent.genlayer.get_last_signal()
        if data:
            await u.message.reply_text(
                "*GenLayer On-Chain:*\n"
                "Pair      : " + data.get("pair", "-") + "/USDC\n"
                "Action    : " + data.get("action", "-") + "\n"
                "Validation: " + data.get("validation", "-") + "\n"
                "Price     : " + str(data.get("price", "-")) + "\n"
                "Strength  : " + str(data.get("strength", "-")) + "%",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await u.message.reply_text(
                "Belum ada data on-chain."
            )

    async def on_callback(self, u, c):
        q = u.callback_query
        await q.answer()
        if q.data.startswith("re_"):
            coin = q.data[3:]
            await q.message.reply_text("Scanning " + coin + "...")
            await self.agent.scan_and_send_single(coin)
        elif q.data.startswith("chain_"):
            data = None
            if self.agent.genlayer:
                data = await self.agent.genlayer.get_last_signal()
            if data:
                await q.message.reply_text(
                    json.dumps(data, indent=2)
                )

    async def send_msg(self, text, markup=None):
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            print(
                f"{Fore.RED}Telegram error: {e}{Style.RESET_ALL}"
            )

    async def stop(self):
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
