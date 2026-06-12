import pandas as pd
import os
from src.logger import log

# --- Robust Path Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

MARKET_DATA_PATH = os.path.join(DATA_DIR, "market_data.csv")
NEWS_DATA_PATH = os.path.join(DATA_DIR, "news_data.csv")

def load_market_data(exchange="BIST30", start_date=None, end_date=None):
    """
    Piyasa verisini yükler.

    start_date ve end_date verilirse: DataCache kullanarak sadece o aralığı
    döndürür ve eksik tarihleri otomatik olarak yfinance'dan çeker.

    Parametre verilmezse: eski davranış, CSV'den tüm veriyi okur
    (geriye dönük uyumluluk için korunmuştur).
    """
    if start_date is not None and end_date is not None:
        log.info(f"[DataLoader] Cache destekli yükleme: {exchange} | {start_date} → {end_date}")
        from src.data_cache import get_market_data
        df = get_market_data(exchange, start_date, end_date)
        if df.empty:
            log.error(f"[DataLoader] Cache'den piyasa verisi alınamadı ({exchange}).")
            raise FileNotFoundError(f"Market data for exchange '{exchange}' could not be retrieved from cache.")
        # Tip dönüşümleri
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=[c for c in numeric_cols if c in df.columns], inplace=True)
        df['Date'] = df['Date'].astype(str)
        _validate_index_ticker(df, exchange)
        return df

    # --- Eski davranış: CSV'den oku ---
    path = os.path.join(DATA_DIR, f"market_data_{exchange}.csv")
    if not os.path.exists(path):
        if exchange == "BIST30" and os.path.exists(MARKET_DATA_PATH):
            path = MARKET_DATA_PATH
            log.info(f"Exchange specific BIST30 market data not found, falling back to default: {path}")
        else:
            log.error(f"Market data for exchange '{exchange}' not found at {path}. Run 'scripts/collect_data.py' first.")
            raise FileNotFoundError(f"Market data for exchange '{exchange}' not found at {path}.")
    else:
        log.info(f"Loading market data for exchange '{exchange}' from: {path}")

    df = pd.read_csv(path)

    # Explicitly convert price and volume columns to numeric types.
    numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df.dropna(subset=numeric_cols, inplace=True)
    df['Date'] = df['Date'].astype(str)

    _validate_index_ticker(df, exchange)
    log.info("Market data loaded and components verified successfully.")
    return df


def _validate_index_ticker(df: pd.DataFrame, exchange: str):
    """Index ticker'ın datasette mevcut olduğunu doğrular."""
    index_ticker = "^NDX" if exchange == "NASDAQ" else "XU030.IS"
    unique_tickers = df['ticker'].unique()
    if index_ticker not in unique_tickers:
        log.error(f"Index ticker '{index_ticker}' is missing from the market dataset.")
        raise FileNotFoundError(
            f"Market data for index '{index_ticker}' is missing. "
            f"Please check your internet connection/VPN and run "
            f"'python scripts/collect_data.py' to download Yahoo Finance data."
        )


def load_news_data(exchange="BIST30", start_date=None, end_date=None):
    """
    Haber verisini yükler.

    start_date ve end_date verilirse: DataCache kullanarak sadece o aralığı
    döndürür ve eksik tarihleri otomatik olarak NewsAPI'dan çeker.

    Parametre verilmezse: eski davranış, CSV'den tüm veriyi okur
    (geriye dönük uyumluluk için korunmuştur).
    """
    if start_date is not None and end_date is not None:
        log.info(f"[DataLoader] Cache destekli haber yüklemesi: {exchange} | {start_date} → {end_date}")
        from src.data_cache import get_news_data
        df = get_news_data(exchange, start_date, end_date)
        # Normalize timezone
        if not df.empty and df['publishedAt'].dt.tz is not None:
            df['publishedAt'] = df['publishedAt'].dt.tz_localize(None)
        log.info("News data loaded from cache successfully.")
        return df

    # --- Eski davranış: CSV'den oku ---
    path = os.path.join(DATA_DIR, f"news_data_{exchange}.csv")
    if not os.path.exists(path):
        if exchange == "BIST30" and os.path.exists(NEWS_DATA_PATH):
            path = NEWS_DATA_PATH
            log.info(f"Exchange specific BIST30 news data not found, falling back to default: {path}")
        else:
            log.error(f"News data for exchange '{exchange}' not found at {path}. Run 'scripts/collect_data.py' first.")
            raise FileNotFoundError(f"News data for exchange '{exchange}' not found at {path}.")
    else:
        log.info(f"Loading news data for exchange '{exchange}' from: {path}")

    df = pd.read_csv(path, parse_dates=['publishedAt'])
    # Normalize timezone to naive
    if df['publishedAt'].dt.tz is not None:
        df['publishedAt'] = df['publishedAt'].dt.tz_localize(None)
    log.info("News data loaded successfully.")
    return df


if __name__ == '__main__':
    log.info("--- Data Loader Example ---")
    try:
        market_data = load_market_data()
        log.info("Market Data Head:")
        log.info(market_data.head())
        log.info(f"\nData Types:\n{market_data.dtypes}")

        news_data = load_news_data()
        log.info("\nNews Data Head:")
        log.info(news_data.head())
    except FileNotFoundError as e:
        log.error(e)
