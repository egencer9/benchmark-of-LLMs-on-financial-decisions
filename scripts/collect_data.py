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

def collect_market_data(exchange, start_date, end_date):
    """
    Fetches historical OHLCV data based on the provided date range for a specific exchange.
    """
    tickers = config.EXCHANGES.get(exchange, {}).get("tickers", [])
    log.info(f"Fetching market data for exchange {exchange} ({tickers}) from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        log.info(f"Created data directory at: {DATA_DIR}")

    all_data = []
    for ticker in tickers:
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
        log.error(f"Market data download failed for all tickers on exchange {exchange}. Aborting.")
        return

    df = pd.concat(all_data, ignore_index=True)
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Save to exchange specific file
    out_path = os.path.join(DATA_DIR, f"market_data_{exchange}.csv")
    df.to_csv(out_path, index=False)
    log.info(f"Market data for {exchange} saved correctly to: {out_path}")

    # For BIST30, also save as default market_data.csv for backward compatibility
    if exchange == "BIST30":
        df.to_csv(MARKET_DATA_PATH, index=False)
        log.info(f"BIST30 market data copied to default: {MARKET_DATA_PATH}")

def collect_news_data(exchange, start_date, end_date):
    """Fetches news articles based on the provided date range (fallback logic)."""
    tickers = config.EXCHANGES.get(exchange, {}).get("tickers", [])
    companies = config.EXCHANGES.get(exchange, {}).get("companies", {})
    log.info(f"Fetching news data for exchange {exchange} ({tickers})")
    if not config.NEWS_API_KEY:
        log.error("NEWS_API_KEY not found. Skipping news collection.")
        return

    newsapi = NewsApiClient(api_key=config.NEWS_API_KEY)
    all_news = []
    for ticker in tickers:
        query = companies.get(ticker, ticker)
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
        log.warning(f"No news articles were collected for exchange {exchange}.")
        return

    df = pd.DataFrame(all_news)
    out_path = os.path.join(DATA_DIR, f"news_data_{exchange}.csv")
    df.to_csv(out_path, index=False)
    log.info(f"News data for {exchange} saved to: {out_path}")

# Turkish financial news RSS feeds (verified working as of 2026-04)
RSS_FEEDS = [
    {"name": "Bloomberg HT", "url": "https://www.bloomberght.com/rss"},
    {"name": "Dünya Gazetesi", "url": "https://www.dunya.com/rss"},
    {"name": "Hürriyet Ekonomi", "url": "https://www.hurriyet.com.tr/rss/ekonomi"},
    {"name": "Milliyet Ekonomi", "url": "https://www.milliyet.com.tr/rss/rssNew/ekonomi.xml"},
]

# Extra Turkish keywords per ticker for BIST30 matching
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
    "XU030.IS": ["enflasyon", "faiz", "tcmb", "merkez bankası", "büyüme", "ekonomi", "cari açık", "tüketici fiyatı", "istihdam", "sanayi üretimi"],
}

def _article_matches_ticker(text: str, ticker: str) -> bool:
    """Return True if the article text contains any keyword for the given ticker."""
    text_lower = text.lower()
    for kw in TICKER_KEYWORDS.get(ticker, []):
        if kw in text_lower:
            return True
    return False

def collect_all_news(exchange, start_date, end_date):
    """Runs both NewsAPI and RSS scrapers, merges results into an exchange specific CSV."""
    frames = []
    tickers = config.EXCHANGES.get(exchange, {}).get("tickers", [])
    companies = config.EXCHANGES.get(exchange, {}).get("companies", {})

    # --- Source 1: NewsAPI (English, historical) ---
    if config.NEWS_API_KEY:
        try:
            newsapi = NewsApiClient(api_key=config.NEWS_API_KEY)
            api_rows = []
            for ticker in tickers:
                query = companies.get(ticker, ticker)
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

    # --- Source 2: Turkish RSS feeds (BIST30 only) ---
    if exchange == "BIST30":
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

                for ticker in tickers:
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
        log.warning(f"No news collected from any source for exchange {exchange}.")
        # Write an empty structure so that loader does not crash
        df = pd.DataFrame(columns=['ticker', 'publishedAt', 'title', 'description', 'content', 'source'])
    else:
        df = pd.concat(frames, ignore_index=True)
        # Normalize to timezone-naive UTC so tz-aware and tz-naive can be compared
        df['publishedAt'] = pd.to_datetime(df['publishedAt'], utc=True).dt.tz_localize(None)
        df.drop_duplicates(subset=["ticker", "publishedAt", "title"], inplace=True)
        df.sort_values("publishedAt", ascending=False, inplace=True)

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    out_path = os.path.join(DATA_DIR, f"news_data_{exchange}.csv")
    df.to_csv(out_path, index=False)
    log.info(f"Combined news for {exchange} saved correctly to: {out_path}")

    # For BIST30, also save as default news_data.csv for backward compatibility
    if exchange == "BIST30":
        df.to_csv(NEWS_DATA_PATH, index=False)
        log.info(f"BIST30 news data copied to default: {NEWS_DATA_PATH}")

if __name__ == "__main__":
    log.info("--- Starting Data Collection Script ---")

    target_end_date = pd.to_datetime(config.EVALUATION_END_DATE)
    target_start_date = target_end_date - timedelta(days=30)

    for exchange in config.EXCHANGES.keys():
        log.info(f"--- Collecting Data for Exchange: {exchange} ---")
        collect_market_data(exchange, target_start_date, target_end_date)
        collect_all_news(exchange, target_start_date, target_end_date)

    log.info("--- Data Collection Finished ---")
