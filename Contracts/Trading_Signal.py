# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import json
from dataclasses import dataclass

@allow_storage
@dataclass
class TradingSignalData:
    pair: str
    action: str
    strength: u8
    price: str
    rsi: str
    ema_trend: str
    validation: str
    reasons: str

class TradingSignal(gl.Contract):
    last_signal: str
    last_pair: str
    last_action: str
    last_strength: u8
    total_signals: u32

    def __init__(self) -> None:
        self.last_signal = ""
        self.last_pair = ""
        self.last_action = "NEUTRAL"
        self.last_strength = u8(0)
        self.total_signals = u32(0)

    @gl.public.write
    def validate_signal(
        self,
        pair: str,
        action: str,
        strength: u8,
        price: str,
        rsi: str,
        ema_trend: str,
        reasons: str,
    ) -> None:
        input_prompt = f"""
You are a professional crypto trading analyst.
Evaluate this perpetual futures trading signal:

Pair: {pair}
Action: {action}
Price: {price}
RSI: {rsi}
EMA Trend: {ema_trend}
Signal Strength: {strength}/100
Reasons: {reasons}

Is the {action} signal valid based on these indicators?
Respond **ONLY** with valid JSON (no other text):
{{
    "validation": "VALID" or "INVALID",
    "reason": "short explanation why"
}}
"""

        criteria = """
validation must be exactly "VALID" or "INVALID" (uppercase).
VALID only if all indicators consistently support the action.
INVALID if there is any contradiction.
"""

        final_result = gl.eq_principle_prompt_non_comparative(
            lambda: gl.exec_prompt(input_prompt),
            task=input_prompt,
            criteria=criteria,
        ).replace("```json", "").replace("```", "").strip()

        result_json = json.loads(final_result)
        validation = result_json.get("validation", "INVALID").strip().upper()
        validation = "VALID" if validation == "VALID" else "INVALID"

        self.last_signal = json.dumps({
            "pair": pair,
            "action": action,
            "strength": int(strength),
            "price": price,
            "rsi": rsi,
            "ema_trend": ema_trend,
            "validation": validation,
            "reasons": reasons,
            "ai_reason": result_json.get("reason", "")
        })

        self.last_pair = pair
        self.last_action = action if validation == "VALID" else "NEUTRAL"
        self.last_strength = strength if validation == "VALID" else u8(0)
        self.total_signals = self.total_signals + u32(1)

    @gl.public.view
    def get_last_signal(self) -> str:
        return self.last_signal

    @gl.public.view
    def get_stats(self) -> str:
        return json.dumps({
            "pair": self.last_pair,
            "action": self.last_action,
            "strength": int(self.last_strength),
            "total": int(self.total_signals),
        })
