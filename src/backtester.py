import pandas as pd
import json
import math
from datetime import timedelta

from src.data_loader import load_market_data, load_news_data
from src.llm_agent import construct_master_prompt, get_llm_decision
from src.logger import log
import config

class Portfolio:
    """Futures trading portfolio."""

    def __init__(self, exchange="NASDAQ", initial_cash=None, trading_approach="Balanced"):
        self.exchange = exchange
        if initial_cash is None:
            initial_cash = config.INITIAL_CASH
        self.initial_cash = initial_cash
        self.cash = initial_cash  # Free cash (not posted as margin)
        self.position_type = "FLAT"  # "LONG", "SHORT", or "FLAT"
        self.entry_price = 0.0
        self.contracts = 0
        
        if exchange == "NASDAQ":
            self.multiplier = config.MULTIPLIER_NASDAQ
        else:
            self.multiplier = config.MULTIPLIER_BIST30
            
        self.history = []
        self.detailed_history = []
        self.trades = []
        self.active_position = None
        
        self.trading_approach = trading_approach
        from src.trading_approach import TradingApproachFactory
        self.approach = TradingApproachFactory.get_approach(trading_approach)
        
        log.info(f"Portfolio initialized for {exchange} with {initial_cash:,.2f} {self.get_currency_symbol()} and approach '{self.approach.name}'")

    def get_currency_symbol(self):
        return "$" if self.exchange == "NASDAQ" else "₺"

    def get_margin_per_contract(self, price):
        if self.exchange == "NASDAQ":
            return config.MARGIN_PER_CONTRACT_NASDAQ
        else:
            # BIST30: margin = 10% of contract value = 10% of (price * 0.1) = price * 0.01
            return price * config.MULTIPLIER_BIST30 * config.MARGIN_PCT_BIST30

    def get_margin_posted(self, price):
        if self.position_type == "FLAT":
            return 0.0
        return self.contracts * self.get_margin_per_contract(self.entry_price)

    def get_unrealized_pnl(self, price):
        if self.position_type == "LONG":
            return (price - self.entry_price) * self.multiplier * self.contracts
        elif self.position_type == "SHORT":
            return (self.entry_price - price) * self.multiplier * self.contracts
        else:
            return 0.0

    def get_equity(self, price):
        margin_posted = self.get_margin_posted(price)
        if getattr(config, 'INTRADAY_ONLY', False):
            unrealized_pnl = self.get_unrealized_pnl(price)
            return self.cash + margin_posted + unrealized_pnl
        else:
            # Since cash is marked-to-market daily in overnight mode, it already includes daily PnLs.
            return self.cash + margin_posted


    def execute_trade(self, decision, price, confidence, date_str, reasoning=""):
        # Override decision if confidence is below strategy threshold
        threshold = self.approach.get_trade_confidence_threshold()
        if decision in ['LONG', 'SHORT'] and confidence < threshold:
            log.info(f"Decision overridden: {decision} -> HOLD (confidence {confidence}% < threshold {threshold}%)")
            decision = 'HOLD'

        current_equity = self.get_equity(price)
        margin_needed = self.get_margin_per_contract(price)
        
        max_capital_at_risk = current_equity * self.approach.get_max_risk_pct()
        max_possible_contracts = math.floor(max_capital_at_risk / margin_needed)
        
        # Position sizing scaled by confidence and approach rules
        target_contracts = self.approach.calculate_position_size(max_possible_contracts, confidence)
        target_contracts = max(getattr(config, 'MIN_CONTRACTS', 1), target_contracts)

        # Check against available cash + margin currently posted
        total_available = self.cash + self.get_margin_posted(price)
        if target_contracts * margin_needed > total_available:
            target_contracts = math.floor(total_available / margin_needed)
            target_contracts = max(config.MIN_CONTRACTS, target_contracts)

        # If decision is HOLD
        if decision == 'HOLD':
            log.info(f"HOLD position. Current position: {self.position_type} ({self.contracts} contracts).")
            return

        # If decision is FLAT
        if decision == 'FLAT':
            if self.position_type != "FLAT":
                self.close_position(price, confidence, date_str, reasoning)
            return

        # If decision is LONG
        if decision == 'LONG':
            if self.position_type == "LONG":
                log.info(f"Already LONG {self.contracts} contracts. Holding.")
                return
            if self.position_type == "SHORT":
                self.close_position(price, confidence, date_str, "Flipping position to LONG.")
            
            # Open LONG
            margin_to_post = target_contracts * margin_needed
            if self.cash >= margin_to_post and target_contracts > 0:
                self.cash -= margin_to_post
                self.position_type = "LONG"
                self.contracts = target_contracts
                self.entry_price = price
                self.active_position = {
                    "ticker": "MNQ" if self.exchange == "NASDAQ" else "VIOP_BIST30",
                    "type": "LONG",
                    "entry_date": date_str,
                    "entry_price": price,
                    "quantity": target_contracts,
                    "confidence": confidence,
                    "reasoning": reasoning
                }
                log.info(f"=== TRADE TAKEN: Opened LONG {target_contracts} contracts @ {price:.2f} (Margin posted: {margin_to_post:,.2f}) ===")
                log.info(f"Entry Reason: {reasoning}")
            else:
                log.warning(f"Insufficient cash to open LONG position. Have {self.cash:,.2f}, need {margin_to_post:,.2f}")

        # If decision is SHORT
        elif decision == 'SHORT':
            if self.position_type == "SHORT":
                log.info(f"Already SHORT {self.contracts} contracts. Holding.")
                return
            if self.position_type == "LONG":
                self.close_position(price, confidence, date_str, "Flipping position to SHORT.")
            
            # Open SHORT
            margin_to_post = target_contracts * margin_needed
            if self.cash >= margin_to_post and target_contracts > 0:
                self.cash -= margin_to_post
                self.position_type = "SHORT"
                self.contracts = target_contracts
                self.entry_price = price
                self.active_position = {
                    "ticker": "MNQ" if self.exchange == "NASDAQ" else "VIOP_BIST30",
                    "type": "SHORT",
                    "entry_date": date_str,
                    "entry_price": price,
                    "quantity": target_contracts,
                    "confidence": confidence,
                    "reasoning": reasoning
                }
                log.info(f"=== TRADE TAKEN: Opened SHORT {target_contracts} contracts @ {price:.2f} (Margin posted: {margin_to_post:,.2f}) ===")
                log.info(f"Entry Reason: {reasoning}")
            else:
                log.warning(f"Insufficient cash to open SHORT position. Have {self.cash:,.2f}, need {margin_to_post:,.2f}")

    def close_position(self, price, confidence, date_str, reasoning):
        pnl = self.get_unrealized_pnl(price)
        margin_posted = self.get_margin_posted(price)
        
        if getattr(config, 'INTRADAY_ONLY', False):
            self.cash += margin_posted + pnl
        else:
            # PnL has already been added to cash daily via mark-to-market in overnight mode
            self.cash += margin_posted
            
        log.info(f"=== TRADE EXIT: Closed {self.contracts} {self.position_type} contracts @ {price:.2f}. Realized PnL: {pnl:,.2f} {self.get_currency_symbol()} ===")
        log.info(f"Exit Reason: {reasoning}")
        
        if self.active_position:
            self.trades.append({
                "ticker": self.active_position["ticker"],
                "decision": self.active_position["type"], # Required by schema (decision maps to LONG/SHORT)
                "price": self.active_position["entry_price"], # Required by schema
                "quantity": self.active_position["quantity"], # Required by schema
                "value": self.active_position["quantity"] * self.active_position["entry_price"] * self.multiplier, # Required by schema
                "confidence": self.active_position["confidence"], # Required by schema
                "reasoning": f"Entry reasoning: {self.active_position['reasoning']}. Exit reasoning: {reasoning}", # Required by schema
                
                # New fields for round-trip trade details
                "entry_date": self.active_position["entry_date"],
                "entry_price": self.active_position["entry_price"],
                "exit_date": date_str,
                "exit_price": price,
                "pnl": pnl
            })
            self.active_position = None
        
        self.position_type = "FLAT"
        self.contracts = 0
        self.entry_price = 0.0

    def update_history(self, date_str, index_price, decision, confidence, daily_pnl, reasoning):
        equity = self.get_equity(index_price)
        margin_posted = self.get_margin_posted(index_price)
        unrealized_pnl = self.get_unrealized_pnl(index_price)
        
        self.history.append(equity)
        
        holdings_dict = {}
        if self.position_type != "FLAT":
            ticker_name = "MNQ" if self.exchange == "NASDAQ" else "VIOP_BIST30"
            holdings_dict[f"{ticker_name}_{self.position_type}"] = self.contracts
            
        self.detailed_history.append({
            "date": date_str,
            "index_price": index_price,
            "decision": decision,
            "confidence": confidence,
            "contracts": self.contracts,
            "position_type": self.position_type,
            "entry_price": self.entry_price,
            "daily_pnl": daily_pnl,
            "equity": equity,
            "cash": self.cash,
            "margin_posted": margin_posted,
            "unrealized_pnl": unrealized_pnl,
            "reasoning": reasoning,
            "holdings": holdings_dict,
            "total_value": equity
        })

def run_backtest(start_date, end_date, model_config=None, return_details=False, exchange="BIST30", trading_approach="Balanced"):
    """Main backtesting loop for futures index trading."""
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

    portfolio = Portfolio(exchange=exchange, trading_approach=trading_approach)

    market_data['Date'] = pd.to_datetime(market_data['Date'])
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    simulation_dates = sorted(market_data['Date'].unique())
    simulation_dates = [d for d in simulation_dates if start_date <= d <= end_date]

    log.info(f"Starting backtest from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({len(simulation_dates)} trading days)")

    index_ticker = "^NDX" if exchange == "NASDAQ" else "XU030.IS"
    yesterday_close = 0.0

    is_intraday = getattr(config, 'INTRADAY_ONLY', False)

    for current_date in simulation_dates:
        date_str = current_date.strftime('%Y-%m-%d')
        log.info(f"--- Trading Day: {date_str} ---")

        day_data = market_data[market_data['Date'] == current_date]
        current_prices = {row['ticker']: row['Close'] for _, row in day_data.iterrows()}
        open_prices = {row['ticker']: row['Open'] for _, row in day_data.iterrows()}

        if not current_prices or index_ticker not in current_prices:
            log.warning(f"No index price for {date_str}. Skipping.")
            portfolio.update_history(date_str, yesterday_close or 0.0, "HOLD", 50, 0.0, "No price data")
            continue

        today_close = current_prices[index_ticker]
        today_open = open_prices.get(index_ticker, today_close)

        # Daily mark-to-market PnL
        daily_pnl = 0.0
        if not is_intraday:
            # Overnight: compute daily mark-to-market PnL from yesterday's close to today's close
            if yesterday_close > 0.0 and portfolio.position_type != "FLAT":
                if portfolio.position_type == "LONG":
                    daily_pnl = (today_close - yesterday_close) * portfolio.multiplier * portfolio.contracts
                elif portfolio.position_type == "SHORT":
                    daily_pnl = (yesterday_close - today_close) * portfolio.multiplier * portfolio.contracts
            
            # Accumulate daily mark-to-market cash flows
            portfolio.cash += daily_pnl
            
            # In overnight mode, the LLM receives the closing price
            daily_market_data = {ticker: {'price': price} for ticker, price in current_prices.items()}
        else:
            # In intraday mode, the LLM receives the opening price
            daily_market_data = {ticker: {'price': open_prices.get(ticker, current_prices[ticker])} for ticker in current_prices.keys()}

        # Daily component data & news summaries
        lookback_start = current_date - timedelta(days=7)
        news_window = news_data[
            (news_data['publishedAt'].dt.date >= lookback_start.date()) &
            (news_data['publishedAt'].dt.date <= current_date.date())
        ]

        daily_news_summaries = {}
        for ticker in current_prices.keys():
            ticker_news = news_window[news_window['ticker'] == ticker]
            if ticker_news.empty:
                # Fallback: strictly query historical news up to current simulation day (no future news!)
                historical_news = news_data[
                    (news_data['ticker'] == ticker) &
                    (news_data['publishedAt'].dt.date <= current_date.date())
                ]
                ticker_news = historical_news.sort_values('publishedAt', ascending=False)
            recent_news = ticker_news.sort_values(by='publishedAt', ascending=False).head(3)
            descriptions = " ".join(recent_news['description'].dropna())
            daily_news_summaries[ticker] = descriptions if descriptions else "No recent news found."

        portfolio_state = {
            'cash': portfolio.cash,
            'equity': portfolio.get_equity(today_open if is_intraday else today_close),
            'available_cash': portfolio.cash,
            'position_type': portfolio.position_type,
            'contracts': portfolio.contracts,
            'entry_price': portfolio.entry_price,
            'unrealized_pnl': portfolio.get_unrealized_pnl(today_open if is_intraday else today_close)
        }

        is_last_day = (current_date == simulation_dates[-1])
        if is_last_day:
            log.info("Last day of backtest. Forcing FLAT decision to close all positions and turn all money into cash.")
            decision_data = {
                "decision": "FLAT",
                "confidence": 100,
                "reasoning": "Forced FLAT on the last day of backtest to leave no open positions and liquidate all assets to cash."
            }
        else:
            master_prompt = construct_master_prompt(portfolio_state, daily_market_data, daily_news_summaries, exchange=exchange, trading_approach=trading_approach)
            available_tickers = list(current_prices.keys())
            
            log.info(f"\n=================== PROMPT SENT TO AI (Date: {date_str}) ===================")
            log.info(master_prompt)
            log.info("=========================================================================\n")
            
            decision_str = get_llm_decision(master_prompt, available_tickers, model_config=model_config)

            log.info(f"\n=================== AI RAW RESPONSE (Date: {date_str}) ===================")
            log.info(decision_str)
            log.info("=========================================================================\n")

            # Parse decision
            from src.llm_agent import parse_llm_response
            decision_data = parse_llm_response(decision_str)
            log.info(f"AI Parsed Decision: {decision_data.get('decision')} | Confidence: {decision_data.get('confidence')}%")
            log.info(f"AI Sentiment/Reasoning: {decision_data.get('reasoning')}")

        # Execute Trade
        if not is_intraday:
            # Overnight: execute trade at the closing price
            portfolio.execute_trade(
                decision=decision_data.get('decision'),
                price=today_close,
                confidence=decision_data.get('confidence', 50),
                date_str=date_str,
                reasoning=decision_data.get('reasoning', '')
            )
            
            portfolio.update_history(
                date_str=date_str,
                index_price=today_close,
                decision=decision_data.get('decision'),
                confidence=decision_data.get('confidence', 50),
                daily_pnl=daily_pnl,
                reasoning=decision_data.get('reasoning', '')
            )
        else:
            # Intraday: execute trade at the opening price
            portfolio.execute_trade(
                decision=decision_data.get('decision'),
                price=today_open,
                confidence=decision_data.get('confidence', 50),
                date_str=date_str,
                reasoning=decision_data.get('reasoning', '')
            )
            
            # End of day: calculate PnL at close and then close the position
            if portfolio.position_type != "FLAT":
                daily_pnl = portfolio.get_unrealized_pnl(today_close)
                
            # Log history before we close the position so that the day's record logs the held position type and margin
            portfolio.update_history(
                date_str=date_str,
                index_price=today_close,
                decision=decision_data.get('decision'),
                confidence=decision_data.get('confidence', 50),
                daily_pnl=daily_pnl,
                reasoning=decision_data.get('reasoning', '')
            )
            
            # Force close the position at today's close price
            if portfolio.position_type != "FLAT":
                portfolio.close_position(
                    price=today_close,
                    confidence=decision_data.get('confidence', 50),
                    date_str=date_str,
                    reasoning=f"Intraday exit. {decision_data.get('reasoning', '')}"
                )
        
        yesterday_close = today_close
        log.info(f"End of day equity: {portfolio.get_equity(today_close):,.2f}")

    # Close any open position at the final day's price to log the final trade (if any remaining)
    if portfolio.position_type != "FLAT":
        last_date_str = simulation_dates[-1].strftime('%Y-%m-%d')
        portfolio.close_position(price=today_close, confidence=50, date_str=last_date_str, reasoning="Simulation ended.")

    log.info("--- Backtest Finished ---")
    if return_details:
        return {
            "history": portfolio.history,
            "detailed_history": portfolio.detailed_history,
            "trades": portfolio.trades
        }
    return portfolio.history
