import pandas as pd
import json
import math
import time

# Artık sys.path ayarına burada gerek yok, main.py bunu yapıyor.

from src.data_loader import load_market_data, load_news_data
from src.llm_agent import construct_master_prompt, get_llm_decision # FIX: Use singular name
from src.logger import log
import config

class Portfolio:
    """Manages the trading portfolio, including cash, holdings, and transactions."""
    def __init__(self, initial_cash=config.INITIAL_CASH):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.holdings = {}
        self.history = []
        log.info(f"Portfolio initialized with ${initial_cash:,.2f} cash.")

    def get_total_value(self, current_prices):
        total_value = self.cash
        for ticker, shares in self.holdings.items():
            total_value += shares * current_prices.get(ticker, 0)
        return total_value

    def update_history(self, current_prices):
        self.history.append(self.get_total_value(current_prices))

    def execute_trade(self, ticker, decision, price, confidence, trade_fraction=0.1):
        total_value = self.get_total_value({ticker: price})
        
        if decision == 'BUY':
            investment_amount = total_value * trade_fraction * confidence
            if self.cash >= investment_amount:
                quantity = math.floor(investment_amount / price)
                if quantity > 0:
                    self.cash -= quantity * price
                    self.holdings[ticker] = self.holdings.get(ticker, 0) + quantity
                    log.info(f"Executed BUY for {quantity} shares of {ticker} at ${price:.2f} (Value: ${quantity * price:,.2f})")
                else:
                    log.info(f"Investment amount for {ticker} is too low to purchase a single share.")
            else:
                log.warning(f"Insufficient cash for BUY of {ticker}. Have ${self.cash:,.2f}, need ${investment_amount:,.2f}")

        elif decision == 'SELL':
            if ticker in self.holdings and self.holdings[ticker] > 0:
                quantity = self.holdings[ticker]
                self.cash += quantity * price
                del self.holdings[ticker]
                log.info(f"Executed SELL for all {quantity} shares of {ticker} at ${price:.2f} (Value: ${quantity * price:,.2f})")
            else:
                log.warning(f"No holdings for {ticker} to SELL.")
        
        elif decision == 'HOLD':
            log.info(f"Decision is to HOLD {ticker}.")
        else:
            log.warning(f"Invalid decision '{decision}' for {ticker}. Skipping.")


def run_backtest(start_date, end_date):
    """Main backtesting loop."""
    try:
        log.info("Loading data for backtest...")
        market_data = load_market_data()
        news_data = load_news_data()
    except FileNotFoundError:
        log.error("Data files not found. Please run 'scripts/collect_data.py' first.")
        return []

    portfolio = Portfolio()

    market_data['Date'] = pd.to_datetime(market_data['Date'])
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    simulation_dates = sorted(market_data['Date'].unique())
    simulation_dates = [d for d in simulation_dates if start_date <= d <= end_date]

    log.info(f"Starting backtest from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} for {len(simulation_dates)} trading days.")

    # --- METRIC TRACKING: Format Compliance ---
    total_llm_calls = 0
    valid_json_responses = 0

    for current_date in simulation_dates:
        # --- FIX: Add a small delay to avoid hitting API rate limits ---
        time.sleep(2)
        log.info(f"--- Trading Day: {current_date.strftime('%Y-%m-%d')} ---")

        day_data = market_data[market_data['Date'] == current_date]
        current_prices = {row['ticker']: row['Close'] for index, row in day_data.iterrows()}
        
        if not current_prices:
            log.warning(f"No market data for {current_date.strftime('%Y-%m-%d')}. Skipping day.")
            portfolio.update_history(current_prices)
            continue

        daily_market_data = {ticker: {'price': price} for ticker, price in current_prices.items()}
        
        news_today = news_data[news_data['publishedAt'].dt.date == current_date.date()]
        daily_news_summaries = {
            ticker: " ".join(news_today[news_today['ticker'] == ticker]['description'].dropna())
            for ticker in current_prices.keys()
        }

        portfolio_state = {'cash': portfolio.cash, 'holdings': portfolio.holdings}
        master_prompt = construct_master_prompt(portfolio_state, daily_market_data, daily_news_summaries)

        available_tickers = list(current_prices.keys())
        # FIX: Call the correct singular function name
        decision_str = get_llm_decision(master_prompt, available_tickers)
        total_llm_calls += 1
        
        try:
            clean_response = decision_str.strip().replace('```json', '').replace('```', '')
            decisions = json.loads(clean_response)
            valid_json_responses += 1 # Başarılı JSON ayrıştırma
            log.info(f"LLM Decisions Parsed: {decisions}")
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            log.error(f"Failed to decode LLM response: {e}. Response was: {decision_str}")
            decisions = {}

        log.info("Executing trades based on LLM decisions...")
        for ticker, decision_data in decisions.items():
            if ticker in current_prices:
                portfolio.execute_trade(
                    ticker=ticker,
                    decision=decision_data.get('decision'),
                    price=current_prices[ticker],
                    confidence=decision_data.get('confidence', 0.5)
                )
            else:
                log.warning(f"LLM returned decision for untracked ticker {ticker}. Ignoring.")

        portfolio.update_history(current_prices)
        log.info(f"End of day portfolio value: ${portfolio.get_total_value(current_prices):,.2f}")

    # --- REPORT: Format Compliance Rate ---
    if total_llm_calls > 0:
        compliance_rate = (valid_json_responses / total_llm_calls) * 100
        log.info(f"--- Format Compliance Report ---")
        log.info(f"Total LLM Calls: {total_llm_calls} | Valid JSON: {valid_json_responses}")
        log.info(f"Format Compliance Rate: {compliance_rate:.2f}%")

    log.info("--- Backtest Finished ---")
    return portfolio.history
