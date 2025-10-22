import os
import finnhub
import time
import csv
from dotenv import load_dotenv
from datetime import datetime, timedelta


# import companies.yaml  <-- THIS LINE WAS REMOVED

def fetch_company_news(finnhub_client, company_list):
    """
    Fetches the top 10 news articles for the last 7 days for each company in the list
    and writes them to a single CSV file.
    """
    output_filename = 'company_news.csv'
    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        news_writer = csv.writer(csvfile)
        news_writer.writerow(['symbol', 'search_date', 'headline', 'summary', 'source', 'url', 'published_at'])
        print(f"Fetching company news and writing to {output_filename}...")

        for company in company_list:
            symbol = company['symbol']
            print(f"-> Getting news for {company['name']} ({symbol})...")

            for i in range(7):
                target_date = datetime.now() - timedelta(days=i)
                date_str = target_date.strftime('%Y-%m-%d')

                daily_news = finnhub_client.company_news(symbol, _from=date_str, to=date_str)

                if daily_news:
                    for article in daily_news[:10]:
                        published_time = datetime.fromtimestamp(article['datetime']).strftime('%Y-%m-%d %H:%M:%S')
                        news_writer.writerow([
                            symbol,
                            date_str,
                            article['headline'],
                            article['summary'],
                            article['source'],
                            article['url'],
                            published_time
                        ])
                time.sleep(1)

    print(f"\n✅ Successfully wrote company news to {output_filename}")


def fetch_general_news(finnhub_client, starting_date, ending_date):
    """
    Fetches the latest general news and writes it to a CSV file.
    NOTE: The Finnhub API for general_news does NOT support date filtering.
    The starting_date and ending_date parameters are ignored.
    """
    output_filename = 'general_news.csv'
    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        news_writer = csv.writer(csvfile)
        news_writer.writerow(['headline', 'summary', 'source', 'url', 'published_at'])
        print(f"\nFetching general news and writing to {output_filename}...")

        general_news = finnhub_client.general_news('general', min_id=0)

        if general_news:
            for article in general_news:
                published_time = datetime.fromtimestamp(article['datetime']).strftime('%Y-%m-%d %H:%M:%S')
                news_writer.writerow([
                    article['headline'],
                    article['summary'],
                    article['source'],
                    article['url'],
                    published_time
                ])

    print(f"✅ Successfully wrote general news to {output_filename}")


# Main execution block
if __name__ == "__main__":
    load_dotenv()
    API_KEY = os.getenv('API_KEY')

    if not API_KEY:
        print("Error: API_KEY not found in .env file.")
    else:
        try:
            finnhub_client = finnhub.Client(api_key=API_KEY)

            with open('../companies.yaml', 'r') as file:
                yaml_data = yaml.safe_load(file)
                company_list = yaml_data['companies']

            fetch_company_news(finnhub_client, company_list)

            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            fetch_general_news(finnhub_client, start_date, end_date)

        except FileNotFoundError:
            print("Error: 'companies.yaml' not found. Please create it first.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")