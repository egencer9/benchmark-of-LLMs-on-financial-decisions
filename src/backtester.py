import pandas as pd
import json
import math
from datetime import timedelta
from src.data_loader import load_market_data, load_news_data
from src.llm_agent import construct_master_prompt, get_llm_decisions # Plural
from src.logger import log
import config

class Portfolio:
    """Manages the trading portfolio."""
    def __init__(self, initial_cash=config.INITIAL_CASH):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.holdings = {}
        self.history = []

    def get_total_value(self, current_prices):
        total_value = self.cash
        for ticker, shares in self.holdings.items():
            total_value += shares * current_prices.get(ticker, 0)
        return total_value

    def update_history(self, current_prices):
        self.history.append(self.get_total_value(current_prices))

    def execute_trade(self, ticker, decision, price, confidence):
        # ... (Same trade logic)
        if decision == 'BUY':
            investment_amount = self.get_total_value({ticker: price}) * 0.1 * confidence
            if self.cash >= investment_amount:
                quantity = math.floor(investment_amount / price)
                if quantity > 0:
                    self.cash -= quantity * price
                    self.holdings[ticker] = self.holdings.get(ticker, 0) + quantity
        elif decision == 'SELL':
            if ticker in self.holdings:
                quantity = self.holdings[ticker]
                self.cash += quantity * price
                del self.holdings[ticker]

def run_backtest(start_date, end_date):
    # ... (Load data logic same as before)
    try:
        log.info("Loading data for backtest...")
        market_data = load_market_data()
        news_data = load_news_data()
    except FileNotFoundError:
        return {} # Return empty dict on error

    # --- MULTI-MODEL SETUP ---
    # Create a portfolio for each active model
    portfolios = {model['alias']: Portfolio() for model in config.OPENROUTER_MODELS}
    log.info(f"Initialized {len(portfolios)} portfolios for models: {list(portfolios.keys())}")

    # ... (Date filtering logic same as before)
    market_data['Date'] = pd.to_datetime(market_data['Date'])
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    simulation_dates = sorted(market_data['Date'].unique())
    simulation_dates = [d for d in simulation_dates if start_date <= d <= end_date]

    for current_date in simulation_dates:
        log.info(f"--- Trading Day: {current_date.strftime('%Y-%m-%d')} ---")
        
        # ... (Data preparation logic same as before)
        day_data = market_data[market_data['Date'] == current_date]
        current_prices = {row['ticker']: row['Close'] for index, row in day_data.iterrows()}
        
        if not current_prices:
            for p in portfolios.values(): p.update_history(current_prices)
            continue

        daily_market_data = {ticker: {'price': price} for ticker, price in current_prices.items()}
        
        # News logic
        lookback_start = current_date - timedelta(days=3)
        news_window = news_data[(news_data['publishedAt'].dt.date >= lookback_start.date()) & (news_data['publishedAt'].dt.date <= current_date.date())]
        daily_news_summaries = {}
        for ticker in current_prices.keys():
            ticker_news = news_window[news_window['ticker'] == ticker].head(3)
            desc = " ".join(ticker_news['description'].dropna())
            daily_news_summaries[ticker] = desc if desc else "No recent news."

        # --- GET DECISIONS FROM ALL MODELS ---
        # We construct one prompt, but send it to all models
        # Note: We use the state of the FIRST portfolio to construct the prompt.
        # Ideally, each model should see its own portfolio state, but for simplicity 
        # and token savings, we show them a generic or initial state, OR we loop.
        # BETTER APPROACH: Loop through models to generate custom prompts if states diverge.
        # BUT FOR SPEED: Let's assume they all see the same market data.
        
        # To be perfectly accurate, we should generate a prompt for EACH model because
        # their 'Current Portfolio' state will differ after the first trade.
        # Let's do that loop. It's safer.
        
        model_decisions = {}
        
        # 1. Construct prompts for each model (since their portfolios differ)
        # 2. Send requests in parallel (we need to update llm_agent to handle a list of prompts? 
        #    No, let's keep it simple. We will send ONE generic prompt with "Cash: $100k" 
        #    to get their *opinion* on the market, then apply that opinion to their specific portfolio.
        #    This saves huge API costs/time vs sending N unique prompts.)
        
        # Construct GENERIC prompt (ignoring specific portfolio holdings for the decision making)
        # We ask: "Given this market data, what would you do?"
        master_prompt = construct_master_prompt({'cash': 100000, 'holdings': {}}, daily_market_data, daily_news_summaries)
        
        # Get decisions from all models in parallel
        raw_results = get_llm_decisions(master_prompt, list(current_prices.keys()))

        # --- EXECUTE TRADES FOR EACH MODEL ---
        for model_alias, response_str in raw_results.items():
            portfolio = portfolios[model_alias]
            try:
                clean_resp = response_str.strip().replace('```json', '').replace('```', '')
                decisions = json.loads(clean_resp)
                
                log.info(f"[{model_alias}] Decisions: {decisions}")
                
                for ticker, decision_data in decisions.items():
                    if ticker in current_prices:
                        portfolio.execute_trade(
                            ticker, 
                            decision_data.get('decision'), 
                            current_prices[ticker], 
                            decision_data.get('confidence', 0.5)
                        )
            except Exception as e:
                log.error(f"[{model_alias}] Failed to parse: {e}")

            portfolio.update_history(current_prices)
            log.info(f"[{model_alias}] Portfolio Value: ${portfolio.history[-1]:,.2f}")

    log.info("--- Backtest Finished ---")
    
    # Return a dictionary of histories: { "Xiaomi": [...], "NVIDIA": [...] }
    return {alias: p.history for alias, p in portfolios.items()}
