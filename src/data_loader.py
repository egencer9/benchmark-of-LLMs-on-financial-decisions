import pandas as pd
import os
from logger import log

DATA_DIR = "data"
MARKET_DATA_PATH = os.path.join(DATA_DIR, "market_data.csv")
NEWS_DATA_PATH = os.path.join(DATA_DIR, "news_data.csv")

def load_market_data():
    """Loads market data from the CSV file."""
    log.info(f"Loading market data from {MARKET_DATA_PATH}")
    if not os.path.exists(MARKET_DATA_PATH):
        log.error(f"Market data not found at {MARKET_DATA_PATH}. Run scripts/collect_data.py first.")
        raise FileNotFoundError(f"Market data not found at {MARKET_DATA_PATH}.")
    df = pd.read_csv(MARKET_DATA_PATH, index_col='Date', parse_dates=True)
    log.info("Market data loaded successfully.")
    return df

def load_news_data():
    """Loads news data from the CSV file."""
    log.info(f"Loading news data from {NEWS_DATA_PATH}")
    if not os.path.exists(NEWS_DATA_PATH):
        log.error(f"News data not found at {NEWS_DATA_PATH}. Run scripts/collect_data.py first.")
        raise FileNotFoundError(f"News data not found at {NEWS_DATA_PATH}.")
    df = pd.read_csv(NEWS_DATA_PATH, parse_dates=['publishedAt'])
    log.info("News data loaded successfully.")
    return df

if __name__ == '__main__':
    # Example usage:
    log.info("--- Data Loader Example ---")
    try:
        market_data = load_market_data()
        log.info("Market Data Head:")
        log.info(market_data.head())

        news_data = load_news_data()
        log.info("News Data Head:")
        log.info(news_data.head())
    except FileNotFoundError as e:
        log.error(e)
