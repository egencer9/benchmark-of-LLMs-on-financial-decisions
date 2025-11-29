import pandas as pd
import json
from data_loader import load_market_data, load_news_data
from llm_agent import summarize_text, construct_master_prompt, get_llm_decision
from logger import log

class Portfolio:
    """Manages the trading portfolio, including cash, holdings, and transactions."""
    def __init__(self, initial_cash=100000):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.holdings = {}  # { 'AAPL': 10, 'MSFT': 5 }
        self.history = [] # Records portfolio value over time
        log.info(f"Portfolio initialized with ${initial_cash:,.2f} cash.")

    def update_value(self, current_prices):
        """Calculates the total current value of the portfolio."""
        total_value = self.cash
        for ticker, shares in self.holdings.items():
            total_value += shares * current_prices.get(ticker, 0)
        self.history.append(total_value)
        return total_value

    def execute_trade(self, ticker, decision, price, quantity=10):
        """Executes a trade based on the LLM's decision."""
        if decision == 'BUY':
            if self.cash >= price * quantity:
                self.cash -= price * quantity
                self.holdings[ticker] = self.holdings.get(ticker, 0) + quantity
                log.info(f"Executed BUY for {quantity} shares of {ticker} at ${price:.2f}")
            else:
                log.warning(f"Insufficient cash to BUY {quantity} shares of {ticker} at ${price:.2f}")
        elif decision == 'SELL':
            if self.holdings.get(ticker, 0) >= quantity:
                self.cash += price * quantity
                self.holdings[ticker] -= quantity
                if self.holdings[ticker] == 0:
                    del self.holdings[ticker]
                log.info(f"Executed SELL for {quantity} shares of {ticker} at ${price:.2f}")
            else:
                log.warning(f"Not enough shares to SELL {ticker}. Have {self.holdings.get(ticker, 0)}, need {quantity}")
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

    simulation_dates = market_data.index.unique()
    simulation_dates = simulation_dates[(simulation_dates >= pd.to_datetime(start_date)) & (simulation_dates <= pd.to_datetime(end_date))]

    log.info(f"Starting backtest from {start_date} to {end_date} for {len(simulation_dates)} trading days.")

    for current_date in simulation_dates:
        log.info(f"--- Trading Day: {current_date.strftime('%Y-%m-%d')} ---")

        # 1. Prepare daily data
        daily_market_data = {}
        current_prices = {}
        tickers = market_data['ticker'].unique()

        for ticker in tickers:
            ticker_data = market_data[(market_data.index == current_date) & (market_data['ticker'] == ticker)]
            if not ticker_data.empty:
                price = ticker_data['Close'].iloc[0]
                current_prices[ticker] = price
                daily_market_data[ticker] = {'price': price}

        if not daily_market_data:
            log.warning(f"No market data available for {current_date.strftime('%Y-%m-%d')}. Skipping day.")
            continue

        # 2. Summarize news
        daily_news_summaries = {}
        news_today = news_data[news_data['publishedAt'].dt.date == current_date.date()]
        for ticker in tickers:
            ticker_news = news_today[news_today['ticker'] == ticker]
            full_text = " ".join(ticker_news['content'].dropna())
            if full_text:
                log.debug(f"Found news for {ticker}. Summarizing...")
                daily_news_summaries[ticker] = summarize_text(full_text)

        # 3. Construct prompt
        portfolio_state = {'cash': portfolio.cash, 'holdings': portfolio.holdings}
        master_prompt = construct_master_prompt(portfolio_state, daily_market_data, daily_news_summaries)

        # 4. Get LLM decision
        llm_response_str = get_llm_decision(master_prompt)
        try:
            # The response might be in a markdown code block
            clean_response = llm_response_str.strip().replace('```json', '').replace('```', '')
            decisions = json.loads(clean_response)
            log.info("Successfully parsed LLM decisions.")
            log.debug(f"Decisions: {decisions}")
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            log.error(f"Failed to decode LLM response: {e}. Response was: {llm_response_str}")
            decisions = {}

        # 5. Execute trades
        log.info("Executing trades based on LLM decisions...")
        for ticker, decision_data in decisions.items():
            if ticker in current_prices:
                portfolio.execute_trade(
                    ticker,
                    decision_data.get('decision'),
                    current_prices[ticker]
                )
            else:
                log.warning(f"LLM returned decision for untracked ticker {ticker}. Ignoring.")

        # 6. Record daily portfolio value
        portfolio_value = portfolio.update_value(current_prices)
        log.info(f"End of day portfolio value: ${portfolio_value:,.2f}")

    log.info("--- Backtest Finished ---")
    return portfolio.history
