# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from genlayer import *


class TradingSignal(gl.Contract):
    last_signal:   str
    last_pair:     str
    last_action:   str
    last_strength: str
    total_signals: str

    def __init__(self) -> None:
        self.last_signal   = ""
        self.last_pair     = ""
        self.last_action   = "NEUTRAL"
        self.last_strength = "0"
        self.total_signals = "0"

    @gl.public.write
    def validate_and_store_signal(
        self,
        pair:      str,
        action:    str,
        strength:  str,
        price:     str,
        rsi:       str,
        macd:      str,
        ema_trend: str,
        reasons:   str,
        tp1:       str,
        tp2:       str,
        sl:        str,
        rr_ratio:  str,
        timeframe: str,
    ) -> None:

        web_result = gl.get_webpage(
            "https://api.hyperliquid.xyz/info",
            mode="text",
        )

        verify_prompt = (
            "You have access to this Hyperliquid market data:\n"
            + web_result[:300]
            + "\n\nThe trading bot reported:\n"
            + "Pair: " + pair + "\n"
            + "Price: " + price + "\n\n"
            + "Does the live market data confirm this price is plausible "
            + "for " + pair + "? Prices within 2 percent range are acceptable.\n"
            + "Reply only one word: PRICE_OK or PRICE_INVALID"
        )

        price_check = gl.exec_prompt(verify_prompt).strip().upper()
        if "PRICE_INVALID" in price_check:
            price_valid = "PRICE_INVALID"
        else:
            price_valid = "PRICE_OK"

        signal_prompt = (
            "You are a professional crypto trading analyst.\n"
            + "Evaluate this perpetual futures signal:\n\n"
            + "Pair: " + pair + "\n"
            + "Timeframe: " + timeframe + "\n"
            + "Action: " + action + "\n"
            + "Price: " + price + "\n"
            + "RSI: " + rsi + "\n"
            + "MACD: " + macd + "\n"
            + "EMA Trend: " + ema_trend + "\n"
            + "TP1: " + tp1 + "\n"
            + "TP2: " + tp2 + "\n"
            + "Stop Loss: " + sl + "\n"
            + "R/R Ratio: " + rr_ratio + "\n"
            + "Signal Strength: " + strength + "/100\n"
            + "Reasons: " + reasons + "\n"
            + "Price Verification: " + price_valid + "\n\n"
            + "Is the " + action + " signal valid based on these indicators?\n"
            + "Reply in JSON only, no markdown fences:\n"
            + "{\"validation\": \"VALID or INVALID\", \"reason\": \"brief explanation\"}"
        )

        criteria = (
            "validation must be VALID or INVALID. "
            "VALID if technical indicators consistently support the action "
            "and price verification passed. "
            "INVALID if indicators contradict the action or price is unverified."
        )

        final_result = gl.eq_principle_prompt_non_comparative(
            lambda: gl.exec_prompt(signal_prompt),
            task=signal_prompt,
            criteria=criteria,
        )
        final_result = final_result.replace("```json", "")
        final_result = final_result.replace("```", "")
        final_result = final_result.strip()

        result_json = json.loads(final_result)
        validation = result_json.get("validation", "INVALID").upper()
        if "VALID" in validation and "INVALID" not in validation:
            validation = "VALID"
        else:
            validation = "INVALID"

        signal_data = {
            "pair":         pair,
            "action":       action,
            "strength":     strength,
            "price":        price,
            "rsi":          rsi,
            "macd":         macd,
            "ema_trend":    ema_trend,
            "tp1":          tp1,
            "tp2":          tp2,
            "sl":           sl,
            "rr_ratio":     rr_ratio,
            "timeframe":    timeframe,
            "validation":   validation,
            "price_verify": price_valid,
            "reasons":      reasons,
        }
        self.last_signal = json.dumps(signal_data)

        self.last_pair = pair
        if validation == "VALID":
            self.last_action = action
        else:
            self.last_action = "NEUTRAL"

        if validation == "VALID":
            self.last_strength = strength
        else:
            self.last_strength = "0"

        self.total_signals = str(int(self.total_signals) + 1)

    @gl.public.view
    def get_last_signal(self) -> str:
        return self.last_signal

    @gl.public.view
    def get_stats(self) -> str:
        stats = {
            "pair":     self.last_pair,
            "action":   self.last_action,
            "strength": self.last_strength,
            "total":    self.total_signals,
        }
        return json.dumps(stats)