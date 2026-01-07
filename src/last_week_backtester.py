from datetime import datetime, timedelta
import sys
import os

# Add the project root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtester import run_backtest
from logger import log
import pandas as pd
from analysis import calculate_metrics, plot_performance, create_buy_and_hold_baseline
from data_loader import load_market_data

TICKERS = ["NDX"] # Focus on Nasdaq 100 (using NDX ticker) for trading/backtesting

def main():
    log.info("--- Starting Last Week Backtest (Gemini 2.5 Flash) ---")
    
    # Calculate dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    log.info(f"Backtesting window: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Run backtest
    portfolio_history = run_backtest(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )
    
    if portfolio_history:
        log.info("Backtest completed successfully.")
        
        # --- Analysis ---
        log.info("--- Starting Performance Analysis ---")

        # 1. Calculate LLM Agent Metrics
        metrics = calculate_metrics(portfolio_history)
        log.info("LLM Agent Metrics:")
        for metric, value in metrics.items():
             log.info(f"- {metric}: {value}")

        # 2. Create and Analyze Buy-and-Hold Baseline
        try:
            market_data = load_market_data()
            market_data['Date'] = pd.to_datetime(market_data['Date'])
            market_data.set_index('Date', inplace=True)
            simulation_dates = market_data.index.unique()
            # Filter dates to match the backtest period
            start_date_pd = pd.to_datetime(start_date)
            end_date_pd = pd.to_datetime(end_date)
            simulation_dates = simulation_dates[(simulation_dates >= start_date_pd) & (simulation_dates <= end_date_pd)]

            initial_value = 100000
            baseline_history = create_buy_and_hold_baseline(initial_value, market_data, TICKERS, simulation_dates)
            baseline_metrics = calculate_metrics(baseline_history)
            log.info("Buy-and-Hold Baseline Metrics:")
            for metric, value in baseline_metrics.items():
                log.info(f"- {metric}: {value}")

            # 3. Plot Results
            log.info("Generating performance plot...")
            plot_performance(portfolio_history, baseline_history)
            log.info("Plot generated and displayed.")

        except FileNotFoundError as e:
            log.error(f"Could not create baseline: {e}")
        except Exception as e:
            log.error(f"An error occurred during analysis: {e}", exc_info=True)
    else:
        log.warning("No backtest results produced (possibly no trading days in range).")

if __name__ == "__main__":
    main()
