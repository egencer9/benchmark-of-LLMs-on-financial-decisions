import sys
import os
from datetime import datetime, timedelta

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
    log.info("--- Starting NASDAQ LLM Trader Simulation (Multi-Model Arena) ---")

    # ... (Date logic same as before)
    try:
        market_data = load_market_data()
        market_data['Date'] = pd.to_datetime(market_data['Date'])
        if market_data.empty: return
        
        available_dates = sorted(market_data['Date'].unique())
        start_date = available_dates[0]
        end_date = available_dates[-1]
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
    except Exception as e:
        log.error(f"Error determining dates: {e}")
        return

    # Run backtest (Returns a dict of histories)
    all_histories = run_backtest(start_date_str, end_date_str)

    if not all_histories:
        log.warning("Backtest produced no results.")
        return

    log.info("--- Performance Analysis ---")

    # Calculate metrics for EACH model
    for model_name, history in all_histories.items():
        log.info(f"--- Metrics for {model_name} ---")
        metrics = calculate_metrics(history)
        for k, v in metrics.items():
            log.info(f"{k}: {v}")

    # Baseline
    baseline_history = []
    try:
        sim_dates = market_data[(market_data['Date'] >= start_date) & (market_data['Date'] <= end_date)]['Date'].unique()
        if len(sim_dates) > 0:
            baseline_history = create_buy_and_hold_baseline(config.INITIAL_CASH, config.TICKERS, market_data, sim_dates)
            
            log.info("--- Metrics for Buy and Hold (Baseline) ---")
            base_metrics = calculate_metrics(baseline_history)
            for k, v in base_metrics.items():
                log.info(f"{k}: {v}")
    except Exception as e:
        log.error(f"Baseline error: {e}")

    # Plot
    plot_performance(all_histories, baseline_history)
    log.info("Multi-model plot generated.")

if __name__ == "__main__":
    main()
