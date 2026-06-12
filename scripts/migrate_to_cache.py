"""
migrate_to_cache.py — Mevcut CSV verilerini parquet cache'e tek seferlik aktarır.

Kullanım:
    python scripts/migrate_to_cache.py

Bu script:
  1. data/market_data_{exchange}.csv → data/cache/market_{exchange}.parquet
  2. data/news_data_{exchange}.csv   → data/cache/news_{exchange}.parquet
  dosyalarına mevcut veriyi kopyalar.

Bir sonraki backtest çalıştırmada bu cache kullanılacak; eksik tarihler
otomatik olarak çekilecek.
"""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.logger import log
from src.data_cache import (
    _ensure_cache_dir, _cache_path, _load_meta, _save_meta, _date_str
)
import config

DATA_DIR = os.path.join(PROJECT_ROOT, "data")


def migrate_exchange(exchange: str):
    log.info(f"=== {exchange} için migrasyon başlıyor ===")
    _ensure_cache_dir()
    meta = _load_meta()

    # --- Market Data ---
    market_csv = os.path.join(DATA_DIR, f"market_data_{exchange}.csv")
    if os.path.exists(market_csv):
        log.info(f"Piyasa CSV okunuyor: {market_csv}")
        df = pd.read_csv(market_csv)
        df['Date'] = pd.to_datetime(df['Date'])

        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        cache_file = _cache_path("market", exchange)
        # Eğer zaten varsa, birleştir
        if os.path.exists(cache_file):
            existing = pd.read_parquet(cache_file)
            existing['Date'] = pd.to_datetime(existing['Date'])
            combined = pd.concat([existing, df], ignore_index=True)
        else:
            combined = df

        combined.drop_duplicates(subset=['Date', 'ticker'], inplace=True)
        combined.sort_values(['ticker', 'Date'], inplace=True)
        combined.reset_index(drop=True, inplace=True)
        combined.to_parquet(cache_file, index=False)

        meta.setdefault(exchange, {})["market"] = {
            "start": _date_str(combined['Date'].min()),
            "end":   _date_str(combined['Date'].max()),
        }
        log.info(f"✓ Piyasa cache yazıldı: {_date_str(combined['Date'].min())} → {_date_str(combined['Date'].max())} ({len(combined)} satır)")
    else:
        log.warning(f"Piyasa CSV bulunamadı: {market_csv} (atlanıyor)")

    # --- News Data ---
    news_csv = os.path.join(DATA_DIR, f"news_data_{exchange}.csv")
    if os.path.exists(news_csv):
        log.info(f"Haber CSV okunuyor: {news_csv}")
        df = pd.read_csv(news_csv, parse_dates=['publishedAt'])
        if df['publishedAt'].dt.tz is not None:
            df['publishedAt'] = df['publishedAt'].dt.tz_localize(None)

        cache_file = _cache_path("news", exchange)
        if os.path.exists(cache_file):
            existing = pd.read_parquet(cache_file)
            existing['publishedAt'] = pd.to_datetime(existing['publishedAt'])
            combined = pd.concat([existing, df], ignore_index=True)
        else:
            combined = df

        combined.drop_duplicates(subset=['ticker', 'publishedAt', 'title'], inplace=True)
        combined.sort_values('publishedAt', ascending=False, inplace=True)
        combined.reset_index(drop=True, inplace=True)
        combined.to_parquet(cache_file, index=False)

        meta.setdefault(exchange, {})["news"] = {
            "start": _date_str(combined['publishedAt'].min()),
            "end":   _date_str(combined['publishedAt'].max()),
        }
        log.info(f"✓ Haber cache yazıldı: {_date_str(combined['publishedAt'].min())} → {_date_str(combined['publishedAt'].max())} ({len(combined)} satır)")
    else:
        log.warning(f"Haber CSV bulunamadı: {news_csv} (atlanıyor)")

    _save_meta(meta)


if __name__ == "__main__":
    log.info("=== CSV → Parquet Cache Migrasyon Scripti ===")
    for exchange in config.EXCHANGES.keys():
        try:
            migrate_exchange(exchange)
        except Exception as e:
            log.error(f"{exchange} migrasyonu başarısız: {e}")

    log.info("=== Migrasyon tamamlandı ===")

    # Sonucu göster
    from src.data_cache import cache_status
    import json
    status = cache_status()
    log.info(f"Cache durumu:\n{json.dumps(status, indent=2, ensure_ascii=False)}")
