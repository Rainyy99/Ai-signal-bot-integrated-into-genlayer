import pandas as pd
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


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series, fast=12, slow=26, signal=9):
    ema_fast   = ema(series, fast)
    ema_slow   = ema(series, slow)
    macd_line  = ema_fast - ema_slow
    signal_line= ema(macd_line, signal)
    histogram  = macd_line - signal_line
    return macd_line, signal_line, histogram


def bbands(series, period=20, std=2):
    mid   = series.rolling(period).mean()
    sigma = series.rolling(period).std()
    upper = mid + std * sigma
    lower = mid - std * sigma
    return upper, mid, lower


def atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()


def stochrsi(series, period=14, smooth_k=3, smooth_d=3):
    r      = rsi(series, period)
    r_min  = r.rolling(period).min()
    r_max  = r.rolling(period).max()
    k_raw  = (r - r_min) / (r_max - r_min).replace(0, np.nan) * 100
    k      = k_raw.rolling(smooth_k).mean()
    d      = k.rolling(smooth_d).mean()
    return k, d


def mfi(high, low, close, volume, period=14):
    typical    = (high + low + close) / 3
    raw_mf     = typical * volume
    pos_mf     = raw_mf.where(typical > typical.shift(), 0)
    neg_mf     = raw_mf.where(typical < typical.shift(), 0)
    pos_sum    = pos_mf.rolling(period).sum()
    neg_sum    = neg_mf.rolling(period).sum()
    mf_ratio   = pos_sum / neg_sum.replace(0, np.nan)
    return 100 - (100 / (1 + mf_ratio))


class TechnicalAnalyzer:
    def analyze(self, coin, df, timeframe):
        if len(df) < 100:
            return None
        df = df.copy()

        close  = df["close"]
        high   = df["high"]
        low    = df["low"]
        volume = df["volume"]

        e9   = ema(close, 9)
        e21  = ema(close, 21)
        e50  = ema(close, 50)
        e200 = ema(close, 200)

        rsi_val               = rsi(close, 14)
        macd_line, macd_sig, macd_hist = macd(close)
        bb_upper, bb_mid, bb_lower     = bbands(close)
        atr_val               = atr(high, low, close, 14)
        stoch_k, stoch_d      = stochrsi(close)
        mfi_val               = mfi(high, low, close, volume, 14)

        last_idx = -1
        prev_idx = -2

        price    = float(close.iloc[last_idx])
        atr_last = float(atr_val.iloc[last_idx])
        if np.isnan(atr_last) or atr_last == 0:
            atr_last = price * 0.01

        e9_v    = float(e9.iloc[last_idx])
        e21_v   = float(e21.iloc[last_idx])
        e50_v   = float(e50.iloc[last_idx])
        e200_v  = float(e200.iloc[last_idx])

        rsi_v   = float(rsi_val.iloc[last_idx])
        if np.isnan(rsi_v):
            rsi_v = 50.0

        ml_v    = float(macd_line.iloc[last_idx])
        ms_v    = float(macd_sig.iloc[last_idx])
        mh_v    = float(macd_hist.iloc[last_idx])
        mh_p    = float(macd_hist.iloc[prev_idx])
        if np.isnan(ml_v): ml_v = 0.0
        if np.isnan(ms_v): ms_v = 0.0
        if np.isnan(mh_v): mh_v = 0.0
        if np.isnan(mh_p): mh_p = 0.0

        bbu_v   = float(bb_upper.iloc[last_idx])
        bbm_v   = float(bb_mid.iloc[last_idx])
        bbl_v   = float(bb_lower.iloc[last_idx])
        if np.isnan(bbu_v): bbu_v = price * 1.02
        if np.isnan(bbl_v): bbl_v = price * 0.98
        if np.isnan(bbm_v): bbm_v = price

        sk_v    = float(stoch_k.iloc[last_idx])
        sd_v    = float(stoch_d.iloc[last_idx])
        if np.isnan(sk_v): sk_v = 50.0
        if np.isnan(sd_v): sd_v = 50.0

        mfi_v   = float(mfi_val.iloc[last_idx])
        if np.isnan(mfi_v): mfi_v = 50.0

        prev_close = float(close.iloc[prev_idx])

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
            bb_pct = (price - bbl_v) / bb_range * 100
            bb_pos = str(round(bb_pct, 0)) + "%"
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
            rb.append(
                "StochRSI Oversold+Cross " + str(round(sk_v, 1))
            )
        elif sk_v > 80 and sk_v < sd_v:
            sw += 15
            rw.append(
                "StochRSI Overbought+Cross " + str(round(sk_v, 1))
            )

        if mfi_v > 60:
            sb += 10
            rb.append("MFI Bullish " + str(round(mfi_v, 1)))
        elif mfi_v < 40:
            sw += 10
            rw.append("MFI Bearish " + str(round(mfi_v, 1)))

        if sb >= sw:
            action   = "LONG"
            strength = min(sb, 100)
            reasons  = rb
            sl_tight = price - atr_last * 1.0
            sl_loose = price - atr_last * 2.0
            tp1      = price + atr_last * 1.5
            tp2      = price + atr_last * 3.0
            tp3      = price + atr_last * 5.0
        else:
            action   = "SHORT"
            strength = min(sw, 100)
            reasons  = rw
            sl_tight = price + atr_last * 1.0
            sl_loose = price + atr_last * 2.0
            tp1      = price - atr_last * 1.5
            tp2      = price - atr_last * 3.0
            tp3      = price - atr_last * 5.0

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
            coin=coin,
            action=action,
            strength=strength,
            price=round(price, 4),
            timeframe=timeframe,
            rsi=round(rsi_v, 2),
            macd=round(ml_v, 6),
            ema_trend=trend,
            bb_position=bb_pos,
            reasons=reasons[:5],
            tp1=round(tp1, 4),
            tp2=round(tp2, 4),
            tp3=round(tp3, 4),
            sl_tight=round(sl_tight, 4),
            sl_loose=round(sl_loose, 4),
            rr_ratio=rr,
            atr=round(atr_last, 4),
            leverage_rec=lev_rec,
            leverage_max=lev_max,
                   )
