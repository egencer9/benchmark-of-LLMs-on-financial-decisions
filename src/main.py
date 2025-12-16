import sys
import os
from datetime import datetime, timedelta

# Projenin ana dizinini Python'un arama yoluna ekle
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import pandas as pd
from src.backtester import run_backtest
from src.analysis import calculate_metrics, plot_performance, create_buy_and_hold_baseline
from src.data_loader import load_market_data
from src.logger import log
import config

def main():
    """
    Main function to run the backtesting simulation and analysis.
    """
    log.info("--- Starting NASDAQ LLM Trader Simulation ---")

    start_date_str = (datetime.now() - timedelta(days=config.SIMULATION_DAYS)).strftime('%Y-%m-%d')
    end_date_str = datetime.now().strftime('%Y-%m-%d')

    portfolio_history = run_backtest(
        start_date=start_date_str,
        end_date=end_date_str
    )

    if not portfolio_history:
        log.warning("Backtest did not produce any results. Exiting.")
        return

    log.info("--- Starting Performance Analysis ---")

    metrics = calculate_metrics(portfolio_history)
    log.info("LLM Agent Metrics:")
    for metric, value in metrics.items():
        log.info(f"- {metric}: {value}")

    baseline_history = []
    try:
        market_data = load_market_data()
        
        market_data['Date'] = pd.to_datetime(market_data['Date'])
        simulation_dates_df = market_data[
            (market_data['Date'] >= pd.to_datetime(start_date_str)) & 
            (market_data['Date'] <= pd.to_datetime(end_date_str))
        ]
        simulation_dates = simulation_dates_df['Date'].unique()

        if len(simulation_dates) > 0:
            baseline_history = create_buy_and_hold_baseline(config.INITIAL_CASH, config.TICKERS, market_data, simulation_dates)
            baseline_metrics = calculate_metrics(baseline_history)
            log.info("Buy-and-Hold Baseline Metrics:")
            for metric, value in baseline_metrics.items():
                log.info(f"- {metric}: {value}")
        else:
            log.warning("No simulation dates found for baseline calculation.")

    except FileNotFoundError as e:
        log.error(f"Could not create baseline: {e}")
    except Exception as e:
        log.error(f"An error occurred during analysis: {e}", exc_info=True)

    log.info("Generating performance plot...")
    plot_performance(portfolio_history, baseline_history)
    log.info("Plot generated and displayed.")


if __name__ == "__main__":
    main()
