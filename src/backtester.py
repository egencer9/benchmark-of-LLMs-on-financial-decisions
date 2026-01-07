import pandas as pd
import json
import math
from datetime import timedelta

# Artık sys.path ayarına burada gerek yok, main.py bunu yapıyor.

from src.data_loader import load_market_data, load_news_data
from src.llm_agent import construct_master_prompt, get_llm_decision
from src.logger import log
import config

class Portfolio:
    """
    Manages the trading portfolio.
    Supports both Spot (Cash) and Futures (Margin) trading modes based on config.
    """
    def __init__(self, initial_cash=config.INITIAL_CASH):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        # Holdings structure: {ticker: {'quantity': int, 'avg_price': float}}
        self.holdings = {} 
        self.history = []
        log.info(f"Portfolio initialized with ${initial_cash:,.2f} cash. Mode: {config.TRADING_MODE}")

    def get_total_value(self, current_prices):
        """
        Calculates total portfolio value.
        Spot: Cash + (Shares * Price)
        Futures: Cash + (Locked Margin) + (Unrealized P&L)
        """
        if config.TRADING_MODE == 'futures':
            # In futures, 'cash' currently holds the Free Cash (Available Balance).
            # We need to add back the Margin Used to get 'Total Account Value' before P&L.
            # Then add Unrealized P&L.
            
            total_equity = self.cash
            
            for ticker, data in self.holdings.items():
                quantity = data['quantity']
                avg_price = data['avg_price']
                current_price = current_prices.get(ticker, avg_price)
                
                # Locked Margin (we deducted this from cash on BUY, so we add it back to represent value)
                margin_used = quantity * config.FUTURES_CONFIG['margin_per_contract']
                total_equity += margin_used
                
                # Unrealized P&L
                multiplier = config.FUTURES_CONFIG['point_multiplier']
                unrealized_pnl = (current_price - avg_price) * multiplier * quantity
                total_equity += unrealized_pnl
                
            return total_equity
        else:
            # Spot Mode (Legacy)
            total_value = self.cash
            for ticker, shares in self.holdings.items():
                if isinstance(shares, dict): # Handle if we accidentally use new structure
                    shares = shares['quantity']
                total_value += shares * current_prices.get(ticker, 0)
            return total_value

    def update_history(self, current_prices):
        self.history.append(self.get_total_value(current_prices))

    def execute_trade(self, ticker, decision, price, confidence, trade_fraction=0.1):
        if config.TRADING_MODE == 'futures':
            self._execute_futures_trade(ticker, decision, price, confidence, trade_fraction)
        else:
            self._execute_spot_trade(ticker, decision, price, confidence, trade_fraction)

    def _execute_futures_trade(self, ticker, decision, price, confidence, trade_fraction):
        # Only trade the configured futures ticker
        # Note: We might receive '^NDX' but we trade 'MNQ' mentally.
        # The ticker argument here comes from market_data keys (likely ^NDX).
        
        margin_req = config.FUTURES_CONFIG['margin_per_contract']
        multiplier = config.FUTURES_CONFIG['point_multiplier']
        
        total_equity = self.get_total_value({ticker: price})
        
        if decision == 'BUY':
            # logic: allocate % of EQUITY to Risk or Margin?
            # User said: "max_risk_per_trade = 1% ... max_contracts = min(floor(risk/stop), hard_cap)"
            # Simplified: Use trade_fraction of Equity to pay for MARGIN.
            
            allocatable_equity = total_equity * trade_fraction * confidence
            max_contracts_by_margin = math.floor(self.cash / margin_req) # limited by free cash
            desired_contracts = math.floor(allocatable_equity / margin_req)
            
            quantity = min(max_contracts_by_margin, desired_contracts)
            
            if quantity > 0:
                cost = quantity * margin_req
                self.cash -= cost
                
                # Update Holdings
                current_holding = self.holdings.get(ticker, {'quantity': 0, 'avg_price': 0.0})
                old_qty = current_holding['quantity']
                old_avg = current_holding['avg_price']
                
                # Weighted Average Price
                new_avg = ((old_qty * old_avg) + (quantity * price)) / (old_qty + quantity)
                
                self.holdings[ticker] = {'quantity': old_qty + quantity, 'avg_price': new_avg}
                
                log.info(f"FUTURES BUY: {quantity} MNQ contracts @ {price:.2f}. "
                         f"Margin Locked: ${cost:,.2f}. Multiplier: ${multiplier}")
            else:
                 log.info(f"FUTURES BUY Skipped: Insufficient cash/equity for margin. Need ${margin_req}, Have Free Cash: ${self.cash:,.2f}")

        elif decision == 'SELL':
            # Sell existing long position
            if ticker in self.holdings:
                holding = self.holdings[ticker]
                qty = holding['quantity']
                avg_price = holding['avg_price']
                
                if qty > 0:
                    # Return Margin
                    margin_returned = qty * margin_req
                    
                    # Realize P&L
                    pnl = (price - avg_price) * multiplier * qty
                    
                    self.cash += margin_returned + pnl
                    del self.holdings[ticker]
                    
                    log.info(f"FUTURES SELL: Closed {qty} contracts @ {price:.2f}. "
                             f"Entry: {avg_price:.2f}. P&L: ${pnl:,.2f}")
                else:
                    log.warning(f"No contracts to sell for {ticker}.")
            else:
                log.warning(f"No position found for {ticker} to SELL.")

        elif decision == 'HOLD':
             log.info(f"FUTURES HOLD {ticker}.")


    def _execute_spot_trade(self, ticker, decision, price, confidence, trade_fraction):
            total_value = self.get_total_value({ticker: price})
            
            if decision == 'BUY':
                investment_amount = total_value * trade_fraction * confidence
                if self.cash >= investment_amount:
                    quantity = math.floor(investment_amount / price)
                    if quantity > 0:
                        self.cash -= quantity * price
                        # Legacy support: store just int if simple, but let's upgrade to dict for consistency if needed
                        # For now, keeping legacy simple int for spot
                        current_qty = self.holdings.get(ticker, 0)
                        if isinstance(current_qty, dict): current_qty = current_qty['quantity']
                        
                        self.holdings[ticker] = current_qty + quantity
                        log.info(f"Executed BUY for {quantity} shares of {ticker} at ${price:.2f} (Value: ${quantity * price:,.2f})")
                    else:
                        log.info(f"Investment amount for {ticker} is too low to purchase a single share.")
                else:
                    log.warning(f"Insufficient cash for BUY of {ticker}. Have ${self.cash:,.2f}, need ${investment_amount:,.2f}")
    
            elif decision == 'SELL':
                current_holdings = self.holdings.get(ticker, 0)
                if isinstance(current_holdings, dict): 
                    quantity = current_holdings['quantity']
                else:
                    quantity = current_holdings
                
                if quantity > 0:
                    self.cash += quantity * price
                    if ticker in self.holdings: del self.holdings[ticker]
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

    for current_date in simulation_dates:
        log.info(f"--- Trading Day: {current_date.strftime('%Y-%m-%d')} ---")

        day_data = market_data[market_data['Date'] == current_date]
        current_prices = {row['ticker']: row['Close'] for index, row in day_data.iterrows()}
        
        if not current_prices:
            log.warning(f"No market data for {current_date.strftime('%Y-%m-%d')}. Skipping day.")
            portfolio.update_history(current_prices)
            continue

        daily_market_data = {ticker: {'price': price} for ticker, price in current_prices.items()}
        
        # --- FIX: Look back 3 days for news to ensure context ---
        lookback_start = current_date - timedelta(days=3)
        news_window = news_data[
            (news_data['publishedAt'].dt.date >= lookback_start.date()) & 
            (news_data['publishedAt'].dt.date <= current_date.date())
        ]
        
        daily_news_summaries = {}
        for ticker in current_prices.keys():
            ticker_news = news_window[news_window['ticker'] == ticker]
            # Take the top 3 most recent news items to avoid token overflow
            recent_news = ticker_news.sort_values(by='publishedAt', ascending=False).head(3)
            descriptions = " ".join(recent_news['description'].dropna())
            
            if descriptions:
                daily_news_summaries[ticker] = descriptions
            else:
                daily_news_summaries[ticker] = "No recent news found."

        portfolio_state = {'cash': portfolio.cash, 'holdings': portfolio.holdings}
        master_prompt = construct_master_prompt(portfolio_state, daily_market_data, daily_news_summaries)

        available_tickers = list(current_prices.keys())
        decision_str = get_llm_decision(master_prompt, available_tickers)
        
        try:
            clean_response = decision_str.strip().replace('```json', '').replace('```', '')
            decisions = json.loads(clean_response)
            log.info(f"LLM Decisions Parsed: {decisions}")
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            log.error(f"Failed to decode LLM response: {e}. Response was: {decision_str}")
            decisions = {}

        log.info("Executing trades based on LLM decisions...")
        for ticker, decision_data in decisions.items():
            # Map "NDX" from LLM JSON to "^NDX" in market data if needed
            trade_ticker = ticker
            if ticker == "NDX" and config.TARGET_TICKER == "^NDX":
                trade_ticker = config.TARGET_TICKER
            
            # CRITICAL: Only allow trading on the target ticker
            if trade_ticker != config.TARGET_TICKER:
                log.warning(f"Ignoring decision for {ticker} (mapped to {trade_ticker}). Only trading {config.TARGET_TICKER}.")
                continue

            if trade_ticker in current_prices:
                portfolio.execute_trade(
                    ticker=trade_ticker,
                    decision=decision_data.get('decision'),
                    price=current_prices[trade_ticker],
                    confidence=decision_data.get('confidence', 0.5)
                )
            else:
                log.warning(f"LLM returned decision for untracked ticker {ticker}. Ignoring.")

        portfolio.update_history(current_prices)
        log.info(f"End of day portfolio value: ${portfolio.get_total_value(current_prices):,.2f}")

    log.info("--- Backtest Finished ---")
    return portfolio.history
