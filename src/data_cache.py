"""
data_cache.py — Akıllı tarih aralığı önbellek (cache) yöneticisi.

Cache mantığı:
  İstenen aralık [A, B], cache'deki aralık [C, D] ise:
  - [A,B] ⊆ [C,D]  → Direkt cache'ten döner (0 API çağrısı)
  - A < C           → [A, C-1] aralığını çekip cache'e ekler
  - B > D           → [D+1, B] aralığını çekip cache'e ekler
  - Cache boş       → [A, B]'nin tamamını çeker

Dosyalar:
  data/cache/market_{exchange}.parquet
  data/cache/news_{exchange}.parquet
  data/cache/cache_meta.json
"""

import os
import sys
import json
import pandas as pd
from datetime import timedelta

from src.logger import log

# --- Path Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_ROOT, "data", "cache")
META_FILE = os.path.join(CACHE_DIR, "cache_meta.json")


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _load_meta() -> dict:
    """Cache meta JSON'unu yükler; yoksa boş dict döner."""
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            log.warning("Cache meta dosyası bozuk, sıfırlanıyor.")
    return {}


def _save_meta(meta: dict):
    _ensure_cache_dir()
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)


def _cache_path(data_type: str, exchange: str) -> str:
    """Parquet dosya yolunu döner. data_type: 'market' veya 'news'"""
    return os.path.join(CACHE_DIR, f"{data_type}_{exchange}.parquet")


def _parse_date(d) -> pd.Timestamp:
    """Parse a date string or Timestamp safely.

    Enforces ISO-8601 (YYYY-MM-DD) format for string inputs to avoid
    ambiguous locale-specific parsing (e.g. DD.MM.YYYY being mis-read
    as YYYY-DD-MM which causes start > end and 0 rows returned).
    """
    if isinstance(d, (pd.Timestamp,)):
        return d
    s = str(d).strip()
    # If already a valid ISO date, use yearfirst=True for safety
    try:
        return pd.to_datetime(s, format="%Y-%m-%d")
    except ValueError:
        pass
    # Fallback: try other common formats explicitly
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return pd.to_datetime(s, format=fmt)
        except ValueError:
            continue
    # Last resort — let pandas guess, but warn
    log.warning(f"[Cache] Ambiguous date string '{s}' — falling back to pd.to_datetime auto-parse. Prefer YYYY-MM-DD.")
    return pd.to_datetime(s)


def _date_str(d: pd.Timestamp) -> str:
    return d.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Piyasa Verisi Cache
# ---------------------------------------------------------------------------

def _fetch_market_range(exchange: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """yfinance'dan belirtilen aralıktaki piyasa verisini çeker."""
    import yfinance as yf
    import config

    tickers = config.EXCHANGES.get(exchange, {}).get("tickers", [])
    log.info(f"[Cache] yfinance'dan piyasa verisi çekiliyor: {exchange} | {_date_str(start)} → {_date_str(end)}")

    all_data = []
    # yfinance end date exclusive — 1 gün ekle
    yf_end = end + timedelta(days=1)

    for ticker in tickers:
        try:
            stock_data = yf.download(ticker, start=start, end=yf_end, progress=False)
            if isinstance(stock_data.columns, pd.MultiIndex):
                stock_data.columns = stock_data.columns.get_level_values(0)
            if stock_data.empty:
                log.warning(f"[Cache] {ticker} için veri bulunamadı.")
                continue
            stock_data.reset_index(inplace=True)
            stock_data["ticker"] = ticker
            all_data.append(stock_data)
        except Exception as e:
            log.error(f"[Cache] {ticker} indirilirken hata: {e}")

    if not all_data:
        return pd.DataFrame()

    df = pd.concat(all_data, ignore_index=True)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def get_market_data(exchange: str, start_date, end_date) -> pd.DataFrame:
    """
    Cache'den piyasa verisini döner; eksik tarihler varsa yfinance'dan çekip cache'e ekler.
    """
    _ensure_cache_dir()
    start = _parse_date(start_date)
    end   = _parse_date(end_date)

    meta       = _load_meta()
    exch_meta  = meta.get(exchange, {})
    mkt_meta   = exch_meta.get("market", {})
    cache_file = _cache_path("market", exchange)

    cached_start = _parse_date(mkt_meta["start"]) if "start" in mkt_meta else None
    cached_end   = _parse_date(mkt_meta["end"])   if "end"   in mkt_meta else None

    # Hangi aralıkların eksik olduğunu hesapla
    fetch_ranges = []

    if cached_start is None:
        log.info(f"[Cache] '{exchange}' piyasa cache'i boş. Tüm aralık çekiliyor.")
        fetch_ranges.append((start, end))
    else:
        if start < cached_start:
            fetch_ranges.append((start, cached_start - timedelta(days=1)))
            log.info(f"[Cache] Sol boşluk tespit edildi: {_date_str(start)} → {_date_str(cached_start - timedelta(days=1))}")
        if end > cached_end:
            fetch_ranges.append((cached_end + timedelta(days=1), end))
            log.info(f"[Cache] Sağ boşluk tespit edildi: {_date_str(cached_end + timedelta(days=1))} → {_date_str(end)}")
        if not fetch_ranges:
            log.info(f"[Cache] '{exchange}' piyasa verisi tamamen cache'de mevcut ✓")

    # Eksik aralıkları çek ve cache'e ekle
    if fetch_ranges:
        existing = pd.read_parquet(cache_file) if os.path.exists(cache_file) else pd.DataFrame()
        new_frames = [existing] if not existing.empty else []

        for (rs, re) in fetch_ranges:
            fetched = _fetch_market_range(exchange, rs, re)
            if not fetched.empty:
                new_frames.append(fetched)

        if new_frames:
            combined = pd.concat(new_frames, ignore_index=True)
            combined["Date"] = pd.to_datetime(combined["Date"])
            combined.drop_duplicates(subset=["Date", "ticker"], inplace=True)
            combined.sort_values(["ticker", "Date"], inplace=True)
            combined.reset_index(drop=True, inplace=True)
            combined.to_parquet(cache_file, index=False)

            # Meta güncelle
            new_cached_start = combined["Date"].min()
            new_cached_end   = combined["Date"].max()
            meta.setdefault(exchange, {})["market"] = {
                "start": _date_str(new_cached_start),
                "end":   _date_str(new_cached_end),
            }
            _save_meta(meta)
            log.info(f"[Cache] Piyasa cache'i güncellendi: {_date_str(new_cached_start)} → {_date_str(new_cached_end)}")
        else:
            log.warning("[Cache] Hiç yeni piyasa verisi çekilemedi; cache değişmedi.")

    # Cache'den istenen aralığı filtrele
    if not os.path.exists(cache_file):
        log.error(f"[Cache] Cache dosyası yok: {cache_file}")
        return pd.DataFrame()

    df = pd.read_parquet(cache_file)
    df["Date"] = pd.to_datetime(df["Date"])
    mask = (df["Date"] >= start) & (df["Date"] <= end)
    result = df[mask].copy().reset_index(drop=True)
    log.info(f"[Cache] Piyasa verisi döndürüldü: {len(result)} satır ({exchange}, {_date_str(start)} → {_date_str(end)})")
    return result


# ---------------------------------------------------------------------------
# Haber Verisi Cache
# ---------------------------------------------------------------------------

def _fetch_news_range(exchange: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """NewsAPI + RSS'ten belirtilen aralıktaki haberleri çeker."""
    # PROJECT_ROOT'u sys.path'e ekle; böylece 'scripts' paketi import edilebilir
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    from scripts.collect_data import collect_all_news as _collect_all_news_raw

    log.info(f"[Cache] Haber verisi çekiliyor: {exchange} | {_date_str(start)} → {_date_str(end)}")
    # collect_all_news dosyaya yazar; biz onu okuyup DataFrame döndüreceğiz
    _collect_all_news_raw(exchange, start.to_pydatetime(), end.to_pydatetime())

    # collect_all_news, data/news_data_{exchange}.csv'ye yazar
    data_dir = os.path.join(PROJECT_ROOT, "data")
    tmp_path = os.path.join(data_dir, f"news_data_{exchange}.csv")
    if not os.path.exists(tmp_path):
        return pd.DataFrame()

    df = pd.read_csv(tmp_path, parse_dates=["publishedAt"])
    if df["publishedAt"].dt.tz is not None:
        df["publishedAt"] = df["publishedAt"].dt.tz_localize(None)
    # Sadece istenen aralığı döndür
    mask = (df["publishedAt"].dt.date >= start.date()) & (df["publishedAt"].dt.date <= end.date())
    return df[mask].copy()


def get_news_data(exchange: str, start_date, end_date) -> pd.DataFrame:
    """
    Cache'den haber verisini döner; eksik tarihler varsa NewsAPI'dan çekip cache'e ekler.
    """
    _ensure_cache_dir()
    start = _parse_date(start_date)
    end   = _parse_date(end_date)

    meta       = _load_meta()
    exch_meta  = meta.get(exchange, {})
    nws_meta   = exch_meta.get("news", {})
    cache_file = _cache_path("news", exchange)

    cached_start = _parse_date(nws_meta["start"]) if "start" in nws_meta else None
    cached_end   = _parse_date(nws_meta["end"])   if "end"   in nws_meta else None

    fetch_ranges = []

    # NewsAPI ücretsiz plan yalnızca son ~30 günü destekler.
    # Bu nedenle sadece son 35 güne kadar olan boşlukları çekmeye çalışırız.
    import datetime as _dt
    api_horizon = pd.Timestamp(_dt.datetime.now()) - timedelta(days=28)  # NewsAPI free plan ~30 days

    if cached_start is None:
        log.info(f"[Cache] '{exchange}' haber cache'i boş. Tüm aralık çekiliyor.")
        effective_start = max(start, api_horizon)
        if effective_start <= end:
            fetch_ranges.append((effective_start, end))
        else:
            log.info(f"[Cache] İstenen aralık NewsAPI erişim sınırının dışında — haber olmadan devam.")
    else:
        if start < cached_start:
            gap_end = cached_start - timedelta(days=1)
            if gap_end < api_horizon:
                log.info(f"[Cache] Haber sol boşluk ({_date_str(start)} → {_date_str(gap_end)}) NewsAPI erişim sınırı dışında — atlanıyor.")
            else:
                effective_gap_start = max(start, api_horizon)
                fetch_ranges.append((effective_gap_start, gap_end))
                log.info(f"[Cache] Haber sol boşluk: {_date_str(effective_gap_start)} → {_date_str(gap_end)}")
        if end > cached_end:
            fetch_ranges.append((cached_end + timedelta(days=1), end))
            log.info(f"[Cache] Haber sağ boşluk: {_date_str(cached_end + timedelta(days=1))} → {_date_str(end)}")
        if not fetch_ranges:
            log.info(f"[Cache] '{exchange}' haber verisi tamamen cache'de mevcut ✓")

    if fetch_ranges:
        existing = pd.read_parquet(cache_file) if os.path.exists(cache_file) else pd.DataFrame()
        new_frames = [existing] if not existing.empty else []

        for (rs, re) in fetch_ranges:
            fetched = _fetch_news_range(exchange, rs, re)
            if not fetched.empty:
                new_frames.append(fetched)

        new_data_added = len(new_frames) > (1 if not existing.empty else 0)
        if new_data_added:
            combined = pd.concat(new_frames, ignore_index=True)
            combined["publishedAt"] = pd.to_datetime(combined["publishedAt"])
            if combined["publishedAt"].dt.tz is not None:
                combined["publishedAt"] = combined["publishedAt"].dt.tz_localize(None)
            combined.drop_duplicates(subset=["ticker", "publishedAt", "title"], inplace=True)
            combined.sort_values("publishedAt", ascending=False, inplace=True)
            combined.reset_index(drop=True, inplace=True)
            combined.to_parquet(cache_file, index=False)

            new_cached_start = combined["publishedAt"].min()
            new_cached_end   = combined["publishedAt"].max()
            meta.setdefault(exchange, {})["news"] = {
                "start": _date_str(new_cached_start),
                "end":   _date_str(new_cached_end),
            }
            _save_meta(meta)
            log.info(f"[Cache] Haber cache'i güncellendi: {_date_str(new_cached_start)} → {_date_str(new_cached_end)}")
        else:
            log.info("[Cache] Yeni haber yok; mevcut cache değişmedi.")


    if not os.path.exists(cache_file):
        log.warning(f"[Cache] Haber cache dosyası yok: {cache_file}. Boş DataFrame döndürülüyor.")
        return pd.DataFrame(columns=["ticker", "publishedAt", "title", "description", "content"])

    df = pd.read_parquet(cache_file)
    df["publishedAt"] = pd.to_datetime(df["publishedAt"])
    if df["publishedAt"].dt.tz is not None:
        df["publishedAt"] = df["publishedAt"].dt.tz_localize(None)

    # Haberleri aralıkla filtrele (7 gün lookback için başlangıcı 7 gün geri al)
    lookback_start = start - timedelta(days=7)
    mask = (df["publishedAt"].dt.normalize() >= lookback_start) & \
           (df["publishedAt"].dt.normalize() <= end)
    result = df[mask].copy().reset_index(drop=True)
    log.info(f"[Cache] Haber verisi döndürüldü: {len(result)} satır ({exchange}, {_date_str(start)} → {_date_str(end)})")
    return result


# ---------------------------------------------------------------------------
# Cache Durum Raporu
# ---------------------------------------------------------------------------

def cache_status() -> dict:
    """Cache'deki mevcut tarih aralıklarını döner."""
    meta = _load_meta()
    if not meta:
        return {"status": "Boş — henüz veri önbelleklenmemiş."}
    return meta
