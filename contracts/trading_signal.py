# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json


COINGECKO_IDS = {
    "BTC":  "bitcoin",
    "ETH":  "ethereum",
    "SOL":  "solana",
    "BNB":  "binancecoin",
    "AVAX": "avalanche-2",
    "ARB":  "arbitrum",
    "OP":   "optimism",
    "WIF":  "dogwifcoin",
}


class TradingSignal(gl.Contract):
    signals:       TreeMap[str, str]
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
        signal_id: str,
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

        # --- Deterministic guard: prevent reuse of an existing signal_id ---
        assert signal_id not in self.signals, "signal_id already used"

        # --- Deterministic field validation (before spending LLM calls) ---
        field_errors = []
        try:
            price_f = float(price)
            if price_f <= 0:
                field_errors.append("price must be positive")
        except ValueError:
            field_errors.append("price is not a valid number")

        try:
            rsi_f = float(rsi)
            if rsi_f < 0 or rsi_f > 100:
                field_errors.append("rsi out of 0-100 range")
        except ValueError:
            field_errors.append("rsi is not a valid number")

        try:
            float(macd)
        except ValueError:
            field_errors.append("macd is not a valid number")

        try:
            rr_f = float(rr_ratio)
            if rr_f < 0:
                field_errors.append("rr_ratio cannot be negative")
        except ValueError:
            field_errors.append("rr_ratio is not a valid number")

        if action != "LONG" and action != "SHORT":
            field_errors.append("action must be LONG or SHORT")

        if len(field_errors) > 0:
            error_reason = "; ".join(field_errors)
            signal_data = {
                "signal_id":  signal_id,
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
                "validation": "INVALID",
                "reasons":    "Field validation failed: " + error_reason,
            }
            signal_json = json.dumps(signal_data)
            self.signals[signal_id] = signal_json
            self.last_signal   = signal_json
            self.last_pair     = pair
            self.last_action   = "NEUTRAL"
            self.last_strength = "0"
            self.total_signals = str(int(self.total_signals) + 1)
            return

        # --- Live market data + LLM consensus ---
        # Note: this runtime uses the newer namespaced API
        # (gl.nondet.web.render / gl.nondet.exec_prompt /
        # gl.eq_principle.prompt_non_comparative). Hyperliquid's /info
        # endpoint only accepts POST (confirmed via HTTP 405 in
        # testing) and gl.nondet.web.render can only do a plain GET,
        # so we use CoinGecko's simple/price endpoint instead, which
        # is a genuine GET-able REST API and also gives us pair-specific
        # data (only that one coin's price) rather than a full dump.
        cg_id = COINGECKO_IDS.get(pair.upper(), "bitcoin")
        market_url = (
            "https://api.coingecko.com/api/v3/simple/price?ids="
            + cg_id
            + "&vs_currencies=usd&include_24hr_change=true"
        )

        def get_answer() -> str:
            web_result = gl.nondet.web.render(market_url, mode="text")
            prompt = (
                "You are a professional crypto trading analyst.\n"
                + "Live market data fetched fresh for " + pair
                + " specifically:\n"
                + web_result[:300] + "\n\n"
                + "Evaluate this perpetual futures signal:\n\n"
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
                + "First locate " + pair + " within the live snapshot "
                + "above and check if the reported price is plausible "
                + "for THAT specific asset (within 3 percent is "
                + "acceptable). Then check if the " + action + " signal "
                + "is valid based on the technical indicators.\n\n"
                + "Reply in JSON only, no markdown fences:\n"
                + "{\"validation\": \"VALID or INVALID\", \"reason\": \"brief explanation\"}"
            )
            return gl.nondet.exec_prompt(prompt)

        task_description = (
            "Evaluate a " + action + " perpetual futures trading signal "
            + "for " + pair + " (timeframe " + timeframe + "). Locate "
            + pair + " specifically within a live multi-asset Hyperliquid "
            + "market snapshot, then judge the signal using that asset's "
            + "live data plus technical indicators (RSI, MACD, EMA trend, "
            + "R/R ratio). Decide whether the signal is VALID or INVALID."
        )

        criteria = (
            "validation must be VALID or INVALID. "
            "VALID if the reported price is plausible for the specific "
            "pair found in the live snapshot and technical indicators "
            "consistently support the action. INVALID if the price looks "
            "wrong for that specific pair or indicators contradict the action."
        )

        final_result = gl.eq_principle.prompt_non_comparative(
            get_answer,
            task=task_description,
            criteria=criteria,
        )
        final_result = final_result.replace("```json", "")
        final_result = final_result.replace("```", "")
        final_result = final_result.strip()

        # Defensive parsing: if the LLM response isn't perfectly
        # formatted JSON (more likely with a longer prompt), don't let
        # an uncaught JSONDecodeError crash the whole transaction.
        # Fall back to a simple keyword scan of the raw text instead.
        validation = "INVALID"
        try:
            result_json = json.loads(final_result)
            raw_validation = result_json.get("validation", "INVALID").upper()
            if "VALID" in raw_validation and "INVALID" not in raw_validation:
                validation = "VALID"
        except Exception:
            upper_text = final_result.upper()
            if "VALID" in upper_text and "INVALID" not in upper_text:
                validation = "VALID"

        signal_data = {
            "signal_id":  signal_id,
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
        signal_json = json.dumps(signal_data)

        self.signals[signal_id] = signal_json
        self.last_signal = signal_json
        self.last_pair   = pair
        if validation == "VALID":
            self.last_action   = action
            self.last_strength = strength
        else:
            self.last_action   = "NEUTRAL"
            self.last_strength = "0"

        self.total_signals = str(int(self.total_signals) + 1)

    @gl.public.view
    def get_signal(self, signal_id: str) -> str:
        if signal_id in self.signals:
            return self.signals[signal_id]
        return ""

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