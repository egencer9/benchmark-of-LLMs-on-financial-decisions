import yfinance as yf
import pandas as pd
from newsapi import NewsApiClient
import os
from datetime import datetime, timedelta
import sys

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import NEWS_API_KEY
from src.logger import log

# Configuration
TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=30) # Collect last 30 days of data
DATA_DIR = "data"
MARKET_DATA_PATH = os.path.join(DATA_DIR, "market_data.csv")
NEWS_DATA_PATH = os.path.join(DATA_DIR, "news_data.csv")

def collect_market_data():
    """Fetches historical OHLCV data for the target stocks."""
    log.info(f"Fetching market data for {TICKERS} from {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        log.info(f"Created data directory at {DATA_DIR}")

    all_data = []
    for ticker in TICKERS:
        log.debug(f"Downloading data for {ticker}")
        stock_data = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
        stock_data['ticker'] = ticker
        all_data.append(stock_data)

    df = pd.concat(all_data)
    df.to_csv(MARKET_DATA_PATH)
    log.info(f"Market data saved to {MARKET_DATA_PATH}")

def collect_news_data():
    """Fetches news articles for the target stocks."""
    log.info(f"Fetching news data for {TICKERS}")
    if not NEWS_API_KEY:
        log.error("NEWS_API_KEY not found. Please set it in your .env file. Skipping news collection.")
        return

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    newsapi = NewsApiClient(api_key=NEWS_API_KEY)
    all_news = []

    for ticker in TICKERS:
        try:
            log.debug(f"Fetching news for {ticker}")
            articles = newsapi.get_everything(
                q=ticker,
                language='en',
                sort_by='publishedAt',
                page_size=100 # Max per request
            )
            for article in articles['articles']:
                all_news.append({
                    'ticker': ticker,
                    'publishedAt': article['publishedAt'],
                    'title': article['title'],
                    'description': article['description'],
                    'content': article['content']
                })
            log.info(f"Found {len(articles['articles'])} articles for {ticker}")
        except Exception as e:
            log.error(f"Could not fetch news for {ticker}. Reason: {e}")

    if not all_news:
        log.warning("No news articles were collected.")
        return

    df = pd.DataFrame(all_news)
    df['publishedAt'] = pd.to_datetime(df['publishedAt'])
    # Filter news for the simulation period
    df = df[(df['publishedAt'].dt.tz_localize(None) >= START_DATE) & (df['publishedAt'].dt.tz_localize(None) <= END_DATE)]
    df.to_csv(NEWS_DATA_PATH, index=False)
    log.info(f"News data saved to {NEWS_DATA_PATH}")


if __name__ == "__main__":
    log.info("--- Starting Data Collection Script ---")
    collect_market_data()
    collect_news_data()
    log.info("--- Data Collection Finished ---")
