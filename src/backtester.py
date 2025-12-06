import pandas as pd
import json
import math
from data_loader import load_market_data, load_news_data
from llm_agent import construct_master_prompt, get_llm_decision
from logger import log

class Portfolio:
    """Manages the trading portfolio, including cash, holdings, and transactions."""
    def __init__(self, initial_cash=100000):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.holdings = {}  # { 'AAPL': 10, 'MSFT': 5 }
        self.history = [] # Records portfolio value over time
        log.info(f"Portfolio initialized with ${initial_cash:,.2f} cash.")

    def get_total_value(self, current_prices):
        """Calculates the total current value of the portfolio (cash + holdings)."""
        total_value = self.cash
        for ticker, shares in self.holdings.items():
            total_value += shares * current_prices.get(ticker, 0)
        return total_value

    def update_history(self, current_prices):
        """Records the current total portfolio value to history."""
        self.history.append(self.get_total_value(current_prices))

    def execute_trade(self, ticker, decision, price, confidence, trade_fraction=0.1):
        """
        Executes a trade using a fractional sizing strategy based on confidence.
        - BUY: Invests a fraction of the portfolio's total value.
        - SELL: Sells all holdings of the specified ticker.
        """
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

    # --- FIX ---
    # Get unique dates from the 'Date' column, not the index
    market_data['Date'] = pd.to_datetime(market_data['Date'])
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    simulation_dates = market_data['Date'].unique()
    simulation_dates = simulation_dates[(simulation_dates >= start_date) & (simulation_dates <= end_date)]

    log.info(f"Starting backtest from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} for {len(simulation_dates)} trading days.")

    for current_date in simulation_dates:
        log.info(f"--- Trading Day: {current_date.strftime('%Y-%m-%d')} ---")

        # 1. Prepare daily data
        daily_market_data = {}
        current_prices = {}
        
        # Filter market data for the current day
        day_data = market_data[market_data['Date'] == current_date]
        tickers = day_data['ticker'].unique()

        for ticker in tickers:
            ticker_data = day_data[day_data['ticker'] == ticker]
            if not ticker_data.empty:
                price = ticker_data['Close'].iloc[0]
                current_prices[ticker] = price
                daily_market_data[ticker] = {'price': price}

        if not daily_market_data:
            log.warning(f"No market data for {current_date.strftime('%Y-%m-%d')}. Skipping day.")
            portfolio.update_history(current_prices)
            continue

        # 2. Aggregate news descriptions
        daily_news_summaries = {}
        news_today = news_data[news_data['publishedAt'].dt.date == current_date.date()]
        for ticker in tickers:
            ticker_news = news_today[news_today['ticker'] == ticker]
            descriptions = " ".join(ticker_news['description'].dropna())
            if descriptions:
                daily_news_summaries[ticker] = descriptions

        # 3. Construct prompt
        portfolio_state = {'cash': portfolio.cash, 'holdings': portfolio.holdings}
        master_prompt = construct_master_prompt(portfolio_state, daily_market_data, daily_news_summaries)

        # 4. Get LLM decision
        llm_response_str = get_llm_decision(master_prompt)
        try:
            clean_response = llm_response_str.strip().replace('```json', '').replace('```', '')
            decisions = json.loads(clean_response)
            # --- IMPROVEMENT: Log the parsed decisions clearly ---
            log.info(f"LLM Decisions Parsed: {decisions}")
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            log.error(f"Failed to decode LLM response: {e}. Response was: {llm_response_str}")
            decisions = {}

        # 5. Execute trades
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

        # 6. Record daily portfolio value
        portfolio.update_history(current_prices)
        log.info(f"End of day portfolio value: ${portfolio.get_total_value(current_prices):,.2f}")

    log.info("--- Backtest Finished ---")
    return portfolio.history
