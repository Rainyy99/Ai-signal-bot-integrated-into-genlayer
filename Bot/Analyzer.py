import pandas as pd
import pandas_ta as ta
import numpy as np
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Signal:
    coin:          str
    action:        str
    strength:      int
    price:         float
    timeframe:     str
    rsi:           float
    macd:          float
    ema_trend:     str
    bb_position:   str
    reasons:       List[str]
    tp1:           float
    tp2:           float
    tp3:           float
    sl_tight:      float
    sl_loose:      float
    rr_ratio:      float
    atr:           float
    leverage_rec:  int
    leverage_max:  int
    funding_rate:  Optional[float] = None
    open_interest: Optional[float] = None

class TechnicalAnalyzer:
    def analyze(self, coin, df, timeframe):
        if len(df) < 100:
            return None
        df = df.copy()
        df.ta.ema(length=9,   append=True)
        df.ta.ema(length=21,  append=True)
        df.ta.ema(length=50,  append=True)
        df.ta.ema(length=200, append=True)
        df.ta.rsi(length=14,  append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        df.ta.atr(length=14,  append=True)
        df.ta.stochrsi(append=True)
        df.ta.mfi(length=14,  append=True)

        last  = df.iloc[-1]
        prev  = df.iloc[-2]
        price = float(last["close"])
        atr   = float(last.get("ATRr_14", price * 0.01))
        sb, sw, rb, rw = 0, 0, [], []

        e9   = float(last.get("EMA_9",   price))
        e21  = float(last.get("EMA_21",  price))
        e50  = float(last.get("EMA_50",  price))
        e200 = float(last.get("EMA_200", price))

        if price > e9 > e21 > e50:
            sb += 25; rb.append("EMA Stack Bullish (9>21>50)")
        if price < e9 < e21 < e50:
            sw += 25; rw.append("EMA Stack Bearish (9<21<50)")
        if price > e200:
            sb += 10; rb.append("Price above EMA200")
        else:
            sw += 10; rw.append("Price below EMA200")

        rsi = float(last.get("RSI_14", 50))
        if 60 <= rsi < 75:
            sb += 15; rb.append(f"RSI Bullish {rsi:.1f}")
        elif rsi >= 75:
            sw += 10; rw.append(f"RSI Overbought {rsi:.1f}")
        elif 25 < rsi <= 40:
            sw += 15; rw.append(f"RSI Bearish {rsi:.1f}")
        elif rsi <= 25:
            sb += 10; rb.append(f"RSI Oversold {rsi:.1f}")

        ml  = float(last.get("MACD_12_26_9",  0))
        ms  = float(last.get("MACDs_12_26_9", 0))
        mh  = float(last.get("MACDh_12_26_9", 0))
        pmh = float(prev.get("MACDh_12_26_9", 0))
        if ml > ms and mh > 0:
            sb += 15; rb.append("MACD Bullish Crossover")
        elif ml < ms and mh < 0:
            sw += 15; rw.append("MACD Bearish Crossover")
        if mh > pmh and mh > 0:
            sb += 5; rb.append("MACD Histogram rising")
        elif mh < pmh and mh < 0:
            sw += 5; rw.append("MACD Histogram falling")

        bbu = float(last.get("BBU_20_2.0", price * 1.02))
        bbl = float(last.get("BBL_20_2.0", price * 0.98))
        bbm = float(last.get("BBM_20_2.0", price))
        bb_range = bbu - bbl
        if bb_range > 0:
            bb_pos_str = f"{(price - bbl) / bb_range * 100:.0f}%"
        else:
            bb_pos_str = "MID"
        if price < bbl:
            sb += 15; rb.append("Price below BB Lower")
        elif price > bbu:
            sw += 15; rw.append("Price above BB Upper")
        elif price > bbm and float(prev["close"]) < bbm:
            sb += 8; rb.append("Price crossed BB Mid upward")

        sk = float(last.get("STOCHRSIk_14_14_3_3", 50))
        sd = float(last.get("STOCHRSId_14_14_3_3", 50))
        if sk < 20 and sk > sd:
            sb += 15; rb.append(f"StochRSI Oversold+Cross {sk:.1f}")
        elif sk > 80 and sk < sd:
            sw += 15; rw.append(f"StochRSI Overbought+Cross {sk:.1f}")

        mfi = last.get("MFI_14", 50)
        if isinstance(mfi, float) and not np.isnan(mfi):
            if mfi > 60:
                sb += 10; rb.append(f"MFI Bullish {mfi:.1f}")
            elif mfi < 40:
                sw += 10; rw.append(f"MFI Bearish {mfi:.1f}")

        if sb >= sw:
            action, strength, reasons = "LONG",  min(sb, 100), rb
            sl_tight = price - atr * 1.0
            sl_loose = price - atr * 2.0
            tp1 = price + atr * 1.5
            tp2 = price + atr * 3.0
            tp3 = price + atr * 5.0
        else:
            action, strength, reasons = "SHORT", min(sw, 100), rw
            sl_tight = price + atr * 1.0
            sl_loose = price + atr * 2.0
            tp1 = price - atr * 1.5
            tp2 = price - atr * 3.0
            tp3 = price - atr * 5.0

        risk   = abs(price - sl_tight)
        reward = abs(tp1 - price)
        rr     = round(reward / risk, 2) if risk > 0 else 0
        trend  = ("BULLISH" if price > e9 > e21 > e50
                  else "BEARISH" if price < e9 < e21 < e50
                  else "MIXED")
        vol_ratio = atr / price
        if vol_ratio > 0.03:
            lev_rec, lev_max = 3, 5
        elif vol_ratio > 0.015:
            lev_rec, lev_max = 5, 10
        else:
            lev_rec, lev_max = 10, 20

        return Signal(
            coin=coin, action=action, strength=strength,
            price=price, timeframe=timeframe,
            rsi=round(rsi, 2), macd=round(ml, 6),
            ema_trend=trend, bb_position=bb_pos_str,
            reasons=reasons[:5],
            tp1=round(tp1, 4), tp2=round(tp2, 4), tp3=round(tp3, 4),
            sl_tight=round(sl_tight, 4), sl_loose=round(sl_loose, 4),
            rr_ratio=rr, atr=round(atr, 4),
            leverage_rec=lev_rec, leverage_max=lev_max,
        )
