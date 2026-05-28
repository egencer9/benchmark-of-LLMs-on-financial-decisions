import pandas as pd
import json
import math
from datetime import timedelta

from src.data_loader import load_market_data, load_news_data
from src.llm_agent import construct_master_prompt, get_llm_decision
from src.logger import log
import config

class Portfolio:
    """Spot trading portfolio."""

    def __init__(self, initial_cash=config.INITIAL_CASH):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.holdings = {}  # {ticker: shares}
        self.history = []
        self.detailed_history = []
        self.trades = []
        log.info(f"Portfolio initialized with {initial_cash:,.2f}")

    def get_total_value(self, current_prices):
        total = self.cash
        for ticker, shares in self.holdings.items():
            total += shares * current_prices.get(ticker, 0)
        return total

    def update_history(self, current_prices, date_str=""):
        total_val = self.get_total_value(current_prices)
        self.history.append(total_val)
        self.detailed_history.append({
            "date": date_str if date_str else str(len(self.history)),
            "total_value": total_val,
            "cash": self.cash,
            "holdings": {k: v for k, v in self.holdings.items() if v > 0}
        })

    def execute_trade(self, ticker, decision, price, confidence, reasoning="", trade_fraction=0.1):
        total_value = self.get_total_value({ticker: price})
        quantity = 0

        if decision == 'BUY':
            investment_amount = total_value * trade_fraction * confidence
            if self.cash >= investment_amount and investment_amount > 0:
                quantity = math.floor(investment_amount / price)
                if quantity > 0:
                    self.cash -= quantity * price
                    self.holdings[ticker] = self.holdings.get(ticker, 0) + quantity
                    log.info(f"BUY {quantity} shares of {ticker} @ {price:.2f} ({quantity * price:,.2f})")
                else:
                    log.info(f"Investment too small for one share of {ticker} ({investment_amount:.2f} < {price:.2f})")
            else:
                log.warning(f"Insufficient cash for BUY {ticker}. Have {self.cash:,.2f}, need {investment_amount:,.2f}")

        elif decision == 'SELL':
            quantity = self.holdings.get(ticker, 0)
            if quantity > 0:
                self.cash += quantity * price
                del self.holdings[ticker]
                log.info(f"SELL {quantity} shares of {ticker} @ {price:.2f} ({quantity * price:,.2f})")
            else:
                log.warning(f"No holdings to SELL for {ticker}.")

        elif decision == 'HOLD':
            log.info(f"HOLD {ticker}.")
        else:
            log.warning(f"Invalid decision '{decision}' for {ticker}. Skipping.")
            return

        self.trades.append({
            "ticker": ticker,
            "decision": decision,
            "price": price,
            "quantity": quantity,
            "value": quantity * price,
            "confidence": confidence,
            "reasoning": reasoning
        })


def run_backtest(start_date, end_date, model_config=None, return_details=False, exchange="BIST30"):
    """Main backtesting loop for spot trading."""
    try:
        log.info(f"Loading market data for exchange '{exchange}' backtest...")
        market_data = load_market_data(exchange=exchange)
    except FileNotFoundError:
        log.error(f"Market data for exchange '{exchange}' not found. Please run collection first.")
        return []

    try:
        news_data = load_news_data(exchange=exchange)
    except FileNotFoundError:
        log.warning(f"News data for exchange '{exchange}' not found — proceeding without news (LLM will rely on price action only).")
        news_data = pd.DataFrame(columns=['ticker', 'publishedAt', 'title', 'description', 'content'])

    portfolio = Portfolio()

    market_data['Date'] = pd.to_datetime(market_data['Date'])
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    simulation_dates = sorted(market_data['Date'].unique())
    simulation_dates = [d for d in simulation_dates if start_date <= d <= end_date]

    log.info(f"Starting backtest from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({len(simulation_dates)} trading days)")

    for current_date in simulation_dates:
        date_str = current_date.strftime('%Y-%m-%d')
        log.info(f"--- Trading Day: {date_str} ---")

        day_data = market_data[market_data['Date'] == current_date]
        current_prices = {row['ticker']: row['Close'] for _, row in day_data.iterrows()}

        if not current_prices:
            log.warning(f"No market data for {date_str}. Skipping.")
            portfolio.update_history(current_prices, date_str)
            continue

        daily_market_data = {ticker: {'price': price} for ticker, price in current_prices.items()}

        # Look back 7 days for news; fall back to the 3 most recent articles if none found
        lookback_start = current_date - timedelta(days=7)
        news_window = news_data[
            (news_data['publishedAt'].dt.date >= lookback_start.date()) &
            (news_data['publishedAt'].dt.date <= current_date.date())
        ]

        daily_news_summaries = {}
        for ticker in current_prices.keys():
            ticker_news = news_window[news_window['ticker'] == ticker]
            if ticker_news.empty:
                # Fallback: use most recent available articles regardless of date
                ticker_news = news_data[news_data['ticker'] == ticker].sort_values('publishedAt', ascending=False)
            recent_news = ticker_news.sort_values(by='publishedAt', ascending=False).head(3)
            descriptions = " ".join(recent_news['description'].dropna())
            daily_news_summaries[ticker] = descriptions if descriptions else "No recent news found."

        portfolio_state = {'cash': portfolio.cash, 'holdings': portfolio.holdings}
        master_prompt = construct_master_prompt(portfolio_state, daily_market_data, daily_news_summaries, exchange=exchange)

        available_tickers = list(current_prices.keys())
        decision_str = get_llm_decision(master_prompt, available_tickers, model_config=model_config)

        try:
            clean_response = decision_str.strip().replace('```json', '').replace('```', '')
            decisions = json.loads(clean_response)
            log.info(f"LLM Decisions Parsed: {decisions}")
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            log.error(f"Failed to decode LLM response: {e}. Response was: {decision_str}")
            decisions = {}

        log.info("Executing trades based on LLM decisions...")
        for ticker, decision_data in decisions.items():
            if ticker not in current_prices:
                log.warning(f"LLM returned decision for unknown ticker '{ticker}'. Ignoring.")
                continue
            portfolio.execute_trade(
                ticker=ticker,
                decision=decision_data.get('decision'),
                price=current_prices[ticker],
                confidence=decision_data.get('confidence', 0.5),
                reasoning=decision_data.get('reasoning', '')
            )

        portfolio.update_history(current_prices, date_str)
        log.info(f"End of day portfolio value: {portfolio.get_total_value(current_prices):,.2f}")

    log.info("--- Backtest Finished ---")
    if return_details:
        return {
            "history": portfolio.history,
            "detailed_history": portfolio.detailed_history,
            "trades": portfolio.trades
        }
    return portfolio.history
