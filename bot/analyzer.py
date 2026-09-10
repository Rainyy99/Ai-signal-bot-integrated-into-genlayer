from dataclasses import dataclass
from typing import Optional, List, Dict


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


def ewm_alpha(values, alpha):
    result = []
    prev = None
    for v in values:
        if prev is None:
            prev = v
        else:
            prev = v * alpha + prev * (1 - alpha)
        result.append(prev)
    return result


def ema(values, period):
    return ewm_alpha(values, 2.0 / (period + 1))


def rsi(closes, period=14):
    gains  = [0.0]
    losses = [0.0]
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(diff if diff > 0 else 0.0)
        losses.append(-diff if diff < 0 else 0.0)
    avg_gain = ewm_alpha(gains, 1.0 / period)
    avg_loss = ewm_alpha(losses, 1.0 / period)
    result = []
    for g, l in zip(avg_gain, avg_loss):
        if l == 0:
            result.append(100.0 if g > 0 else 50.0)
        else:
            rs = g / l
            result.append(100 - (100 / (1 + rs)))
    return result


def macd(closes, fast=12, slow=26, signal=9):
    ema_fast    = ema(closes, fast)
    ema_slow    = ema(closes, slow)
    macd_line   = [a - b for a, b in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal)
    hist        = [a - b for a, b in zip(macd_line, signal_line)]
    return macd_line, signal_line, hist


def rolling_mean_std(values, period):
    means = [None] * len(values)
    stds  = [None] * len(values)
    for i in range(len(values)):
        if i + 1 >= period:
            window = values[i - period + 1:i + 1]
            m = sum(window) / period
            if period > 1:
                var = sum((x - m) ** 2 for x in window) / (period - 1)
            else:
                var = 0.0
            means[i] = m
            stds[i]  = var ** 0.5
    return means, stds


def bbands(closes, period=20, std_mult=2):
    means, stds = rolling_mean_std(closes, period)
    upper, mid, lower = [], [], []
    for m, s, c in zip(means, stds, closes):
        if m is None:
            upper.append(c * 1.02)
            mid.append(c)
            lower.append(c * 0.98)
        else:
            upper.append(m + std_mult * s)
            mid.append(m)
            lower.append(m - std_mult * s)
    return upper, mid, lower


def atr(highs, lows, closes, period=14):
    tr = []
    for i in range(len(closes)):
        if i == 0:
            tr.append(highs[i] - lows[i])
        else:
            tr.append(max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            ))
    return ewm_alpha(tr, 1.0 / period)


def rolling_min_max(values, period):
    mins = [None] * len(values)
    maxs = [None] * len(values)
    for i in range(len(values)):
        if i + 1 >= period:
            window = values[i - period + 1:i + 1]
            mins[i] = min(window)
            maxs[i] = max(window)
    return mins, maxs


def rolling_mean(values, period):
    result = [None] * len(values)
    for i in range(len(values)):
        if i + 1 >= period:
            window = values[i - period + 1:i + 1]
            result[i] = sum(window) / period
    return result


def stochrsi(closes, period=14, smooth_k=3, smooth_d=3):
    rsi_vals = rsi(closes, period)
    r_min, r_max = rolling_min_max(rsi_vals, period)
    k_raw = []
    for i in range(len(rsi_vals)):
        if r_min[i] is None or r_max[i] == r_min[i]:
            k_raw.append(50.0)
        else:
            k_raw.append((rsi_vals[i] - r_min[i]) / (r_max[i] - r_min[i]) * 100)
    k_smooth = rolling_mean(k_raw, smooth_k)
    k_filled = [v if v is not None else 50.0 for v in k_smooth]
    d_smooth = rolling_mean(k_filled, smooth_d)
    d_filled = [v if v is not None else 50.0 for v in d_smooth]
    return k_filled, d_filled


def mfi(highs, lows, closes, volumes, period=14):
    typical = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    raw_mf  = [t * v for t, v in zip(typical, volumes)]
    pos_mf  = [0.0]
    neg_mf  = [0.0]
    for i in range(1, len(typical)):
        if typical[i] > typical[i - 1]:
            pos_mf.append(raw_mf[i])
            neg_mf.append(0.0)
        elif typical[i] < typical[i - 1]:
            pos_mf.append(0.0)
            neg_mf.append(raw_mf[i])
        else:
            pos_mf.append(0.0)
            neg_mf.append(0.0)

    pos_sum = [None] * len(pos_mf)
    neg_sum = [None] * len(neg_mf)
    for i in range(len(pos_mf)):
        if i + 1 >= period:
            pos_sum[i] = sum(pos_mf[i - period + 1:i + 1])
            neg_sum[i] = sum(neg_mf[i - period + 1:i + 1])

    result = []
    for p, n in zip(pos_sum, neg_sum):
        if p is None:
            result.append(50.0)
        elif n == 0:
            result.append(100.0 if p > 0 else 50.0)
        else:
            ratio = p / n
            result.append(100 - (100 / (1 + ratio)))
    return result


class TechnicalAnalyzer:
    def analyze(self, coin, candles, timeframe):
        if len(candles) < 100:
            return None

        closes  = [c["close"]  for c in candles]
        highs   = [c["high"]   for c in candles]
        lows    = [c["low"]    for c in candles]
        volumes = [c["volume"] for c in candles]

        e9   = ema(closes, 9)
        e21  = ema(closes, 21)
        e50  = ema(closes, 50)
        e200 = ema(closes, 200)

        rsi_vals   = rsi(closes, 14)
        ml, ms, mh = macd(closes)
        bbu, bbm, bbl = bbands(closes)
        atr_vals   = atr(highs, lows, closes, 14)
        sk, sd     = stochrsi(closes)
        mfi_vals   = mfi(highs, lows, closes, volumes, 14)

        price      = closes[-1]
        atr_last   = atr_vals[-1] if atr_vals[-1] else price * 0.01
        e9_v, e21_v, e50_v, e200_v = e9[-1], e21[-1], e50[-1], e200[-1]
        rsi_v      = rsi_vals[-1]
        ml_v, ms_v, mh_v, mh_p = ml[-1], ms[-1], mh[-1], mh[-2]
        bbu_v, bbm_v, bbl_v    = bbu[-1], bbm[-1], bbl[-1]
        sk_v, sd_v = sk[-1], sd[-1]
        mfi_v      = mfi_vals[-1]
        prev_close = closes[-2]

        sb, sw, rb, rw = 0, 0, [], []

        if price > e9_v > e21_v > e50_v:
            sb += 25
            rb.append("EMA Stack Bullish (9>21>50)")
        if price < e9_v < e21_v < e50_v:
            sw += 25
            rw.append("EMA Stack Bearish (9<21<50)")
        if price > e200_v:
            sb += 10
            rb.append("Price above EMA200")
        else:
            sw += 10
            rw.append("Price below EMA200")

        if 60 <= rsi_v < 75:
            sb += 15
            rb.append("RSI Bullish " + str(round(rsi_v, 1)))
        elif rsi_v >= 75:
            sw += 10
            rw.append("RSI Overbought " + str(round(rsi_v, 1)))
        elif 25 < rsi_v <= 40:
            sw += 15
            rw.append("RSI Bearish " + str(round(rsi_v, 1)))
        elif rsi_v <= 25:
            sb += 10
            rb.append("RSI Oversold " + str(round(rsi_v, 1)))

        if ml_v > ms_v and mh_v > 0:
            sb += 15
            rb.append("MACD Bullish Crossover")
        elif ml_v < ms_v and mh_v < 0:
            sw += 15
            rw.append("MACD Bearish Crossover")
        if mh_v > mh_p and mh_v > 0:
            sb += 5
            rb.append("MACD Histogram rising")
        elif mh_v < mh_p and mh_v < 0:
            sw += 5
            rw.append("MACD Histogram falling")

        bb_range = bbu_v - bbl_v
        if bb_range > 0:
            bb_pos = str(round((price - bbl_v) / bb_range * 100, 0)) + "%"
        else:
            bb_pos = "MID"
        if price < bbl_v:
            sb += 15
            rb.append("Price below BB Lower")
        elif price > bbu_v:
            sw += 15
            rw.append("Price above BB Upper")
        elif price > bbm_v and prev_close < bbm_v:
            sb += 8
            rb.append("Price crossed BB Mid upward")

        if sk_v < 20 and sk_v > sd_v:
            sb += 15
            rb.append("StochRSI Oversold+Cross " + str(round(sk_v, 1)))
        elif sk_v > 80 and sk_v < sd_v:
            sw += 15
            rw.append("StochRSI Overbought+Cross " + str(round(sk_v, 1)))

        if mfi_v > 60:
            sb += 10
            rb.append("MFI Bullish " + str(round(mfi_v, 1)))
        elif mfi_v < 40:
            sw += 10
            rw.append("MFI Bearish " + str(round(mfi_v, 1)))

        if sb >= sw:
            action, strength, reasons = "LONG", min(sb, 100), rb
            sl_tight = price - atr_last * 1.0
            sl_loose = price - atr_last * 2.0
            tp1 = price + atr_last * 1.5
            tp2 = price + atr_last * 3.0
            tp3 = price + atr_last * 5.0
        else:
            action, strength, reasons = "SHORT", min(sw, 100), rw
            sl_tight = price + atr_last * 1.0
            sl_loose = price + atr_last * 2.0
            tp1 = price - atr_last * 1.5
            tp2 = price - atr_last * 3.0
            tp3 = price - atr_last * 5.0

        risk   = abs(price - sl_tight)
        reward = abs(tp1 - price)
        rr     = round(reward / risk, 2) if risk > 0 else 0

        if price > e9_v > e21_v > e50_v:
            trend = "BULLISH"
        elif price < e9_v < e21_v < e50_v:
            trend = "BEARISH"
        else:
            trend = "MIXED"

        vol_ratio = atr_last / price
        if vol_ratio > 0.03:
            lev_rec, lev_max = 3, 5
        elif vol_ratio > 0.015:
            lev_rec, lev_max = 5, 10
        else:
            lev_rec, lev_max = 10, 20

        return Signal(
            coin=coin, action=action, strength=strength,
            price=round(price, 4), timeframe=timeframe,
            rsi=round(rsi_v, 2), macd=round(ml_v, 6),
            ema_trend=trend, bb_position=bb_pos,
            reasons=reasons[:5],
            tp1=round(tp1, 4), tp2=round(tp2, 4), tp3=round(tp3, 4),
            sl_tight=round(sl_tight, 4), sl_loose=round(sl_loose, 4),
            rr_ratio=rr, atr=round(atr_last, 4),
            leverage_rec=lev_rec, leverage_max=lev_max,
        )