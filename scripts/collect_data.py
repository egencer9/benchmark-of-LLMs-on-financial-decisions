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

def collect_market_data(start_date, end_date):
    """
    Fetches historical OHLCV data based on the provided date range.
    """
    log.info(f"Fetching market data for {config.TICKERS} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        log.info(f"Created data directory at: {DATA_DIR}")

    all_data = []
    for ticker in config.TICKERS:
        log.debug(f"Downloading data for {ticker}")
        try:
            stock_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
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
    df['Date'] = pd.to_datetime(df['Date'])
    df.to_csv(MARKET_DATA_PATH, index=False)
    log.info(f"Market data saved correctly to: {MARKET_DATA_PATH}")

def collect_news_data(start_date, end_date):
    """Fetches news articles based on the provided date range."""
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
                from_param=start_date.strftime('%Y-%m-%d'),
                to=end_date.strftime('%Y-%m-%d'),
                language='en',
                sort_by='publishedAt'
            )
            for article in articles['articles']:
                all_news.append({
                    'ticker': ticker, 'publishedAt': article['publishedAt'], 'title': article['title'],
                    'description': article['description'], 'content': article['content']
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
    log.info("--- Starting Data Collection Script ---")
    
    # --- FIX: Calculate dates once and pass them to both functions ---
    # This ensures absolute consistency between market and news data periods.
    target_end_date = pd.to_datetime(config.EVALUATION_END_DATE)
    target_start_date = target_end_date - timedelta(days=30)
    
    collect_market_data(target_start_date, target_end_date)
    collect_news_data(target_start_date, target_end_date)
    
    log.info("--- Data Collection Finished ---")
