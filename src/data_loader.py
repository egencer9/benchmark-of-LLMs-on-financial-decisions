import pandas as pd
import os
from src.logger import log

# --- Robust Path Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

MARKET_DATA_PATH = os.path.join(DATA_DIR, "market_data.csv")
NEWS_DATA_PATH = os.path.join(DATA_DIR, "news_data.csv")

def load_market_data(exchange="BIST30"):
    """
    Loads market data from the CSV file and ensures correct data types.
    """
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
    
    # --- FIX ---
    # Explicitly convert price and volume columns to numeric types.
    # This prevents errors if pandas misinterprets the column type.
    numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce') # 'coerce' turns non-numeric values into NaN
    
    # Drop rows with any NaN values that might have resulted from conversion errors
    df.dropna(subset=numeric_cols, inplace=True)
    
    log.info("Market data loaded and numeric columns converted successfully.")
    return df

def load_news_data(exchange="BIST30"):
    """Loads news data from the CSV file using an absolute path."""
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
