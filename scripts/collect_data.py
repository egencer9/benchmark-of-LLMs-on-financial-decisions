import yfinance as yf
import pandas as pd
from newsapi import NewsApiClient
import os
from datetime import datetime, timedelta
import sys
import feedparser
import requests
import time

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

            # --- FIX: Flatten MultiIndex columns if present (recent yfinance update) ---
            if isinstance(stock_data.columns, pd.MultiIndex):
                stock_data.columns = stock_data.columns.get_level_values(0)

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
        # Use company name for better news search results (BIST tickers like THYAO.IS don't match news well)
        query = config.COMPANY_NAMES.get(ticker, ticker)
        # NewsAPI free tier only supports English
        for lang in ['en']:
            try:
                articles = newsapi.get_everything(
                    q=query,
                    from_param=start_date.strftime('%Y-%m-%d'),
                    to=end_date.strftime('%Y-%m-%d'),
                    language=lang,
                    sort_by='publishedAt'
                )
                for article in articles['articles']:
                    all_news.append({
                        'ticker': ticker, 'publishedAt': article['publishedAt'], 'title': article['title'],
                        'description': article['description'], 'content': article['content']
                    })
                log.info(f"Found {len(articles['articles'])} {lang.upper()} articles for {ticker} (query: '{query}')")
            except Exception as e:
                log.error(f"Could not fetch {lang} news for {ticker}. Reason: {e}")

    if not all_news:
        log.warning("No news articles were collected.")
        return

    df = pd.DataFrame(all_news)
    df.to_csv(NEWS_DATA_PATH, index=False)
    log.info(f"News data saved to: {NEWS_DATA_PATH}")

# Turkish financial news RSS feeds (verified working as of 2026-04)
RSS_FEEDS = [
    {"name": "Bloomberg HT", "url": "https://www.bloomberght.com/rss"},
    {"name": "Dünya Gazetesi", "url": "https://www.dunya.com/rss"},
    {"name": "Hürriyet Ekonomi", "url": "https://www.hurriyet.com.tr/rss/ekonomi"},
    {"name": "Milliyet Ekonomi", "url": "https://www.milliyet.com.tr/rss/rssNew/ekonomi.xml"},
]

# Extra Turkish keywords per ticker for better matching
TICKER_KEYWORDS = {
    "AKBNK.IS": ["akbank", "akbnk"],
    "ARCLK.IS": ["arçelik", "arcelik", "arclk", "beko"],
    "ASELS.IS": ["aselsan", "asels"],
    "BIMAS.IS": ["bim", "bimas", "bim mağaza"],
    "CCOLA.IS": ["coca-cola içecek", "ccola", "cci"],
    "DOHOL.IS": ["doğan holding", "dogan holding", "dohol"],
    "EKGYO.IS": ["emlak konut", "ekgyo"],
    "EREGL.IS": ["ereğli", "eregli", "erdemir", "eregl"],
    "FROTO.IS": ["ford otosan", "froto"],
    "GARAN.IS": ["garanti", "garanti bbva", "garan"],
    "HALKB.IS": ["halkbank", "halk bankası", "halkb"],
    "ISCTR.IS": ["iş bankası", "is bankasi", "isctr", "işbank"],
    "KCHOL.IS": ["koç holding", "koc holding", "kchol"],
    "KRDMD.IS": ["kardemir", "krdmd"],
    "MGROS.IS": ["migros", "mgros"],
    "OTKAR.IS": ["otokar", "otkar"],
    "PETKM.IS": ["petkim", "petkm"],
    "PGSUS.IS": ["pegasus", "pgsus"],
    "SAHOL.IS": ["sabancı holding", "sabanci holding", "sahol"],
    "SASA.IS": ["sasa polyester", "sasa"],
    "SISE.IS": ["şişecam", "sisecam", "sise"],
    "SOKM.IS": ["şok market", "sok market", "sokm"],
    "TAVHL.IS": ["tav havalimanları", "tav airports", "tavhl"],
    "TCELL.IS": ["turkcell", "tcell"],
    "THYAO.IS": ["türk hava yolları", "thy", "turkish airlines", "thyao"],
    "TKFEN.IS": ["tekfen", "tkfen"],
    "TOASO.IS": ["tofaş", "tofas", "toaso"],
    "TUPRS.IS": ["tüpraş", "tupras", "tuprs"],
    "VAKBN.IS": ["vakıfbank", "vakifbank", "vakbn"],
    "YKBNK.IS": ["yapı kredi", "yapi kredi", "ykbnk"],
}


def _article_matches_ticker(text: str, ticker: str) -> bool:
    """Return True if the article text contains any keyword for the given ticker."""
    text_lower = text.lower()
    for kw in TICKER_KEYWORDS.get(ticker, []):
        if kw in text_lower:
            return True
    return False


def collect_news_data_rss(start_date, end_date):
    """Fetches news articles from Turkish financial RSS feeds within the date range."""
    log.info(f"Fetching RSS news from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    headers = {"User-Agent": "Mozilla/5.0 (compatible; LLM-Benchmark-Bot/1.0)"}
    all_news = []

    for feed_info in RSS_FEEDS:
        log.info(f"Parsing feed: {feed_info['name']} ({feed_info['url']})")
        try:
            response = requests.get(feed_info["url"], headers=headers, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except Exception as e:
            log.warning(f"Could not fetch {feed_info['name']}: {e}")
            continue

        articles_in_range = 0
        for entry in feed.entries:
            # Parse published date
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])

            if published is None:
                continue

            published_dt = pd.to_datetime(published)
            if not (start_date <= published_dt <= end_date):
                continue

            title = getattr(entry, "title", "") or ""
            description = getattr(entry, "summary", "") or ""
            content = title + " " + description

            for ticker in config.TICKERS:
                if _article_matches_ticker(content, ticker):
                    all_news.append({
                        "ticker": ticker,
                        "publishedAt": published_dt,
                        "title": title,
                        "description": description,
                        "content": content,
                        "source": feed_info["name"],
                    })
                    articles_in_range += 1

        log.info(f"  → {articles_in_range} matching articles from {feed_info['name']}")
        time.sleep(1)  # polite delay between feeds

    if not all_news:
        log.warning("No RSS articles matched any BIST30 ticker. Check feed URLs and keywords.")
        return

    df = pd.DataFrame(all_news)
    df.drop_duplicates(subset=["ticker", "publishedAt", "title"], inplace=True)
    df.to_csv(NEWS_DATA_PATH, index=False)
    log.info(f"RSS news data saved: {len(df)} rows → {NEWS_DATA_PATH}")


def collect_all_news(start_date, end_date):
    """Runs both NewsAPI and RSS scrapers, merges results into a single CSV."""
    frames = []

    # --- Source 1: NewsAPI (English, historical) ---
    if config.NEWS_API_KEY:
        try:
            newsapi = NewsApiClient(api_key=config.NEWS_API_KEY)
            api_rows = []
            for ticker in config.TICKERS:
                query = config.COMPANY_NAMES.get(ticker, ticker)
                try:
                    articles = newsapi.get_everything(
                        q=query,
                        from_param=start_date.strftime('%Y-%m-%d'),
                        to=end_date.strftime('%Y-%m-%d'),
                        language='en',
                        sort_by='publishedAt'
                    )
                    for a in articles['articles']:
                        api_rows.append({
                            'ticker': ticker,
                            'publishedAt': pd.to_datetime(a['publishedAt']),
                            'title': a['title'],
                            'description': a['description'],
                            'content': a['content'],
                            'source': 'NewsAPI',
                        })
                    log.info(f"NewsAPI: {len(articles['articles'])} EN articles for {ticker}")
                except Exception as e:
                    log.warning(f"NewsAPI failed for {ticker}: {e}")
            if api_rows:
                frames.append(pd.DataFrame(api_rows))
        except Exception as e:
            log.warning(f"NewsAPI client init failed: {e}")
    else:
        log.warning("NEWS_API_KEY not set — skipping NewsAPI.")

    # --- Source 2: Turkish RSS feeds ---
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LLM-Benchmark-Bot/1.0)"}
    rss_rows = []
    for feed_info in RSS_FEEDS:
        log.info(f"Fetching RSS: {feed_info['name']}")
        try:
            response = requests.get(feed_info["url"], headers=headers, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except Exception as e:
            log.warning(f"Could not fetch {feed_info['name']}: {e}")
            continue

        matched = 0
        for entry in feed.entries:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])
            if published is None:
                continue

            published_dt = pd.to_datetime(published)
            title = getattr(entry, "title", "") or ""
            description = getattr(entry, "summary", "") or ""
            content = title + " " + description

            for ticker in config.TICKERS:
                if _article_matches_ticker(content, ticker):
                    rss_rows.append({
                        "ticker": ticker,
                        "publishedAt": published_dt,
                        "title": title,
                        "description": description,
                        "content": content,
                        "source": feed_info["name"],
                    })
                    matched += 1
        log.info(f"  → {matched} matched articles from {feed_info['name']}")
        time.sleep(1)

    if rss_rows:
        frames.append(pd.DataFrame(rss_rows))

    # --- Merge & save ---
    if not frames:
        log.warning("No news collected from any source.")
        return

    df = pd.concat(frames, ignore_index=True)
    # Normalize to timezone-naive UTC so tz-aware and tz-naive can be compared
    df['publishedAt'] = pd.to_datetime(df['publishedAt'], utc=True).dt.tz_localize(None)
    df.drop_duplicates(subset=["ticker", "publishedAt", "title"], inplace=True)
    df.sort_values("publishedAt", ascending=False, inplace=True)

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    df.to_csv(NEWS_DATA_PATH, index=False)
    log.info(f"Combined news saved: {len(df)} rows ({df['source'].value_counts().to_dict()}) → {NEWS_DATA_PATH}")


if __name__ == "__main__":
    log.info("--- Starting Data Collection Script ---")

    target_end_date = pd.to_datetime(config.EVALUATION_END_DATE)
    target_start_date = target_end_date - timedelta(days=30)

    collect_market_data(target_start_date, target_end_date)
    collect_all_news(target_start_date, target_end_date)

    log.info("--- Data Collection Finished ---")
