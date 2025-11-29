
import pandas as pd
import os

# Find the project root directory (go up one level since this file is in /src)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')


def load_all_data():
    """
    Reads all CSV data, sets the datetime columns,
    and returns them as DataFrames.
    """
    print("Loading data...")

    # --- Load Market Data ---
    market_data_path = os.path.join(DATA_DIR, 'market_data.csv')
    try:
        # Read 'Date' column as datetime and set it as index
        market_df = pd.read_csv(
            market_data_path,
            parse_dates=['Date'],  # Convert 'Date' column to datetime object
            index_col='Date'  # Set 'Date' column as the main index
        )
        # Simplify column names (fix multi-level headers from yfinance)
        market_df.columns = [col[1] if isinstance(col, tuple) else col for col in market_df.columns]
        # Get only Open and P/E data for BIST30 (example)
        # You must adjust this part according to your own market_data.csv structure.
        # Assuming 'Open' and 'P/E' for simplicity.

        print(f"Successfully loaded '{market_data_path}'.")
    except Exception as e:
        print(f"ERROR: Could not load '{market_data_path}'. Did you run 'scripts/collect_data.py'? Error: {e}")
        market_df = pd.DataFrame()  # Return an empty DataFrame on error

    # --- Load News Data ---
    news_data_path = os.path.join(DATA_DIR, 'general_news.csv')
    try:
        # Read 'published_at' column as datetime
        news_df = pd.read_csv(
            news_data_path,
            parse_dates=['published_at']  # Convert 'published_at' column to datetime object
        )
        print(f"Successfully loaded '{news_data_path}'.")
    except Exception as e:
        print(f"ERROR: Could not load '{news_data_path}'. Error: {e}")
        news_df = pd.DataFrame()  # Return an empty DataFrame on error

    return market_df, news_df


if __name__ == '__main__':
    # You can test this file quickly by running it directly
    market_data, news_data = load_all_data()

    print("\n--- Market Data (First 5 Rows) ---")
    print(market_data.head())

    print("\n--- News Data (First 5 Rows) ---")
    print(news_data.head())