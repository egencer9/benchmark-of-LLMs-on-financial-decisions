import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

end = datetime.now()
start = end - timedelta(days=30)
tickers_to_test = ["NDX", "QQQ"]
for ticker in tickers_to_test:
    print(f"Testing {ticker}...")
    data = yf.download(ticker, start=start, end=end)
    print(f"{ticker} Empty?", data.empty)
print(data.head())
print("Columns:", data.columns)

if not data.empty:
    print("Download successful.")
else:
    print("Download failed (empty).")
