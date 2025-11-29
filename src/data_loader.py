import pandas as pd
import os
from logger import log

# --- Robust Path Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

MARKET_DATA_PATH = os.path.join(DATA_DIR, "market_data.csv")
NEWS_DATA_PATH = os.path.join(DATA_DIR, "news_data.csv")

def load_market_data():
    """
    Loads market data from the CSV file and ensures correct data types.
    """
    log.info(f"Attempting to load market data from absolute path: {MARKET_DATA_PATH}")
    if not os.path.exists(MARKET_DATA_PATH):
        log.error(f"Market data not found at {MARKET_DATA_PATH}. Run 'scripts/collect_data.py' first.")
        raise FileNotFoundError(f"Market data not found at {MARKET_DATA_PATH}.")
    
    df = pd.read_csv(MARKET_DATA_PATH)
    
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

def load_news_data():
    """Loads news data from the CSV file using an absolute path."""
    log.info(f"Attempting to load news data from absolute path: {NEWS_DATA_PATH}")
    if not os.path.exists(NEWS_DATA_PATH):
        log.error(f"News data not found at {NEWS_DATA_PATH}. Run 'scripts/collect_data.py' first.")
        raise FileNotFoundError(f"News data not found at {NEWS_DATA_PATH}.")
    
    df = pd.read_csv(NEWS_DATA_PATH, parse_dates=['publishedAt'])
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
