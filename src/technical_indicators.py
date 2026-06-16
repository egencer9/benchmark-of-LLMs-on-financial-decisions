"""
technical_indicators.py — Teknik analiz göstergeleri hesaplama modülü.

Mevcut OHLCV verisinden RSI, SMA, MACD, Bollinger %B ve fiyat değişim
yüzdelerini hesaplar. Ek kütüphane gerektirmez (sadece pandas + numpy).

Kullanım:
    get_index_ta_summary(market_data, "^NDX", current_date, "$")
    → "RSI(14): 72.30 — Overbought ..."

    get_stock_ta_brief(market_data, "AAPL", current_date)
    → "5D: +1.23% | RSI: 55.30"
"""

import numpy as np
import pandas as pd
from src.logger import log


def _get_close_series(market_data: pd.DataFrame, ticker: str, end_date, min_periods: int = 14) -> pd.Series:
    """Belirli bir ticker için end_date'e kadar olan kapanış fiyatları serisini döner."""
    df = market_data[market_data['ticker'] == ticker].copy()
    df['Date'] = pd.to_datetime(df['Date'])
    df = df[df['Date'] <= pd.Timestamp(end_date)]
    df = df.sort_values('Date')
    df = df.drop_duplicates(subset=['Date'], keep='last')

    if len(df) < min_periods:
        log.debug(f"[TA] {ticker}: Yetersiz veri ({len(df)} < {min_periods} gün)")
        return pd.Series(dtype=float)

    return df.set_index('Date')['Close']


def compute_rsi(close_series: pd.Series, period: int = 14) -> float:
    """14 günlük RSI hesaplar. Yeterli veri yoksa 50.0 (nötr) döner."""
    if len(close_series) < period + 1:
        return 50.0

    delta = close_series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    # Wilder's smoothed moving average (EMA-based)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))

    last_rsi = rsi.iloc[-1]
    return round(float(last_rsi), 2) if not np.isnan(last_rsi) else 50.0


def compute_sma(close_series: pd.Series, period: int) -> float:
    """Basit hareketli ortalama hesaplar."""
    if len(close_series) < period:
        return float(close_series.iloc[-1]) if len(close_series) > 0 else 0.0

    return round(float(close_series.rolling(window=period).mean().iloc[-1]), 2)


def compute_macd(close_series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """MACD line, signal line ve histogram hesaplar."""
    if len(close_series) < slow + signal:
        return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}

    ema_fast = close_series.ewm(span=fast, adjust=False).mean()
    ema_slow = close_series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return {
        "macd": round(float(macd_line.iloc[-1]), 2),
        "signal": round(float(signal_line.iloc[-1]), 2),
        "histogram": round(float(histogram.iloc[-1]), 2),
    }


def compute_bollinger_pctb(close_series: pd.Series, period: int = 20, std_dev: float = 2.0) -> float:
    """Bollinger Band %B değeri hesaplar (0=alt bant, 0.5=orta, 1=üst bant)."""
    if len(close_series) < period:
        return 0.5  # Nötr

    sma = close_series.rolling(window=period).mean()
    std = close_series.rolling(window=period).std()
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)

    current_price = close_series.iloc[-1]
    upper_val = upper.iloc[-1]
    lower_val = lower.iloc[-1]

    if upper_val == lower_val:
        return 0.5

    pctb = (current_price - lower_val) / (upper_val - lower_val)
    return round(float(pctb), 4)


def compute_price_changes(close_series: pd.Series) -> dict:
    """1, 5 ve 10 günlük fiyat değişim yüzdeleri."""
    result = {}
    current = close_series.iloc[-1] if len(close_series) > 0 else 0.0

    for days, label in [(1, "1d"), (5, "5d"), (10, "10d")]:
        if len(close_series) > days:
            prev = close_series.iloc[-(days + 1)]
            if prev != 0:
                pct = ((current - prev) / prev) * 100
                result[label] = round(float(pct), 2)
            else:
                result[label] = 0.0
        else:
            result[label] = 0.0

    return result


def _rsi_label(rsi_val: float) -> str:
    """RSI değeri için insan-okunabilir etiket."""
    if rsi_val >= 70:
        return "Overbought"
    elif rsi_val <= 30:
        return "Oversold"
    elif rsi_val >= 60:
        return "Bullish"
    elif rsi_val <= 40:
        return "Bearish"
    else:
        return "Neutral"


def _macd_label(histogram: float) -> str:
    """MACD histogram'ı için yön etiketi."""
    if histogram > 0:
        return "Bullish Momentum"
    elif histogram < 0:
        return "Bearish Momentum"
    return "Neutral"


def _bollinger_label(pctb: float) -> str:
    """Bollinger %B için yorumlayıcı etiket."""
    if pctb >= 0.8:
        return "Near Upper Band (potential resistance)"
    elif pctb <= 0.2:
        return "Near Lower Band (potential support)"
    elif pctb >= 0.6:
        return "Upper half of range"
    elif pctb <= 0.4:
        return "Lower half of range"
    return "Mid-range"


def get_index_ta_summary(market_data: pd.DataFrame, index_ticker: str, current_date, currency_symbol: str = "$") -> str:
    """
    İndeks ticker'ı için tam teknik analiz özeti üretir.
    Prompt'a doğrudan enjekte edilebilecek formatlı string döner.
    """
    close = _get_close_series(market_data, index_ticker, current_date, min_periods=14)
    if close.empty:
        return "Technical indicators unavailable (insufficient historical data)."

    rsi = compute_rsi(close)
    sma20 = compute_sma(close, 20)
    sma50 = compute_sma(close, 50)
    macd = compute_macd(close)
    pctb = compute_bollinger_pctb(close)
    changes = compute_price_changes(close)

    sma_signal = "Bullish (SMA20 > SMA50)" if sma20 > sma50 else "Bearish (SMA20 < SMA50)"

    lines = [
        f"- RSI(14): {rsi:.2f} — {_rsi_label(rsi)} (>70: overbought, <30: oversold)",
        f"- SMA20: {currency_symbol}{sma20:,.2f} / SMA50: {currency_symbol}{sma50:,.2f} — {sma_signal}",
        f"- MACD: {macd['macd']:+.2f} / Signal: {macd['signal']:+.2f} / Histogram: {macd['histogram']:+.2f} — {_macd_label(macd['histogram'])}",
        f"- Bollinger %B: {pctb:.4f} — {_bollinger_label(pctb)} (0=lower, 0.5=middle, 1=upper band)",
        f"- Price Change: 1D: {changes['1d']:+.2f}% / 5D: {changes['5d']:+.2f}% / 10D: {changes['10d']:+.2f}%",
    ]
    return "\n".join(lines)


def get_stock_ta_brief(market_data: pd.DataFrame, ticker: str, current_date) -> str:
    """
    Bireysel hisse ticker'ı için kısa teknik özet üretir.
    Hisse satırına eklenecek formatta string döner.
    """
    close = _get_close_series(market_data, ticker, current_date, min_periods=6)
    if close.empty:
        return ""

    changes = compute_price_changes(close)
    rsi = compute_rsi(close)

    return f"5D: {changes['5d']:+.2f}% | RSI: {rsi:.1f}"
