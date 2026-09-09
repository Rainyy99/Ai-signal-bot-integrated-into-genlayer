# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json


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

        def get_answer() -> str:
            web_result = gl.get_webpage(
                "https://api.hyperliquid.xyz/info",
                mode="text",
            )
            prompt = (
                "You are a professional crypto trading analyst.\n"
                + "You have access to this Hyperliquid market data:\n"
                + web_result[:300]
                + "\n\nEvaluate this perpetual futures signal:\n\n"
                + "Pair: " + pair + "\n"
                + "Timeframe: " + timeframe + "\n"
                + "Action: " + action + "\n"
                + "Reported Price: " + price + "\n"
                + "RSI: " + rsi + "\n"
                + "MACD: " + macd + "\n"
                + "EMA Trend: " + ema_trend + "\n"
                + "TP1: " + tp1 + "\n"
                + "TP2: " + tp2 + "\n"
                + "Stop Loss: " + sl + "\n"
                + "R/R Ratio: " + rr_ratio + "\n"
                + "Signal Strength: " + strength + "/100\n"
                + "Reasons: " + reasons + "\n\n"
                + "First check if the reported price is plausible given the "
                + "market data above (within 2 percent is acceptable). "
                + "Then check if the " + action + " signal is valid based on "
                + "the technical indicators.\n\n"
                + "Reply in JSON only, no markdown fences:\n"
                + "{\"validation\": \"VALID or INVALID\", \"reason\": \"brief explanation\"}"
            )
            return gl.exec_prompt(prompt)

        task_description = (
            "Evaluate a " + action + " perpetual futures trading signal "
            + "for " + pair + " using live Hyperliquid market data and "
            + "technical indicators (RSI, MACD, EMA trend, R/R ratio). "
            + "Decide whether the signal is VALID or INVALID."
        )

        criteria = (
            "validation must be VALID or INVALID. "
            "VALID if the price is plausible and technical indicators "
            "consistently support the action. "
            "INVALID if the price looks wrong or indicators contradict the action."
        )

        final_result = gl.eq_principle_prompt_non_comparative(
            get_answer,
            task=task_description,
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
            "pair":       pair,
            "action":     action,
            "strength":   strength,
            "price":      price,
            "rsi":        rsi,
            "macd":       macd,
            "ema_trend":  ema_trend,
            "tp1":        tp1,
            "tp2":        tp2,
            "sl":         sl,
            "rr_ratio":   rr_ratio,
            "timeframe":  timeframe,
            "validation": validation,
            "reasons":    reasons,
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
