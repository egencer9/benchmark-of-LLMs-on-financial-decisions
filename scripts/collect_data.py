import yfinance as yf
import pandas as pd
from newsapi import NewsApiClient
import os
from datetime import datetime, timedelta
import sys

# Projenin ana dizinini Python yoluna ekle
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import config
from src.logger import log

# --- Robust Path Configuration ---
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MARKET_DATA_PATH = os.path.join(DATA_DIR, "market_data.csv")
NEWS_DATA_PATH = os.path.join(DATA_DIR, "news_data.csv")

def collect_market_data():
    """
    Fetches historical OHLCV data based on the evaluation end date in config.
    """
    # --- FIX: Use the resolved evaluation end date from config ---
    end_date = config.resolve_evaluation_end_date()          # datetime.date
    start_date = end_date - timedelta(days=30)               # datetime.date

    # yfinance 'end' is typically exclusive -> add 1 day to include end_date
    yf_end_date = end_date + timedelta(days=1)

    log.info(
        f"Fetching market data for {config.TICKERS} "
        f"from {start_date.isoformat()} to {end_date.isoformat()}"
    )
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        log.info(f"Created data directory at: {DATA_DIR}")

    all_data = []
    for ticker in config.TICKERS:
        log.debug(f"Downloading data for {ticker}")
        try:
            stock_data = yf.download(
                ticker,
                start=start_date.isoformat(),
                end=yf_end_date.isoformat(),
                progress=False
            )

            if stock_data.empty:
                log.warning(f"No data downloaded for {ticker}.")
                continue

            stock_data.reset_index(inplace=True)
            stock_data['ticker'] = ticker
            all_data.append(stock_data)
        except Exception as e:
            log.error(f"An error occurred while downloading data for {ticker}: {e}")

    if not all_data:
        log.error("Market data download failed for all tickers. Aborting.")
        return

    df = pd.concat(all_data, ignore_index=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df.to_csv(MARKET_DATA_PATH, index=False)
    log.info(f"Market data saved correctly to: {MARKET_DATA_PATH}")

def collect_news_data():
    """Fetches news articles based on the evaluation end date in config."""
    # --- FIX: Use the resolved evaluation end date from config ---
    end_date = config.resolve_evaluation_end_date()          # datetime.date
    start_date = end_date - timedelta(days=30)               # datetime.date

    log.info(f"Fetching news data for {config.TICKERS}")
    if not config.NEWS_API_KEY:
        log.error("NEWS_API_KEY not found. Skipping news collection.")
        return

    newsapi = NewsApiClient(api_key=config.NEWS_API_KEY)
    all_news = []
    for ticker in config.TICKERS:
        try:
            articles = newsapi.get_everything(
                q=ticker,
                from_param=start_date.isoformat(),
                to=end_date.isoformat(),
                language='en',
                sort_by='publishedAt'
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
    df.to_csv(NEWS_DATA_PATH, index=False)
    log.info(f"News data saved to: {NEWS_DATA_PATH}")

if __name__ == "__main__":
    log.info("--- Starting Data Collection Script (using fixed date) ---")
    collect_market_data()
    collect_news_data()
    log.info("--- Data Collection Finished ---")
