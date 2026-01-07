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

    # --- FIX: Determine simulation dates directly from the data ---
    try:
        log.info("Loading market data to determine simulation period...")
        market_data = load_market_data()
        market_data['Date'] = pd.to_datetime(market_data['Date'])
        
        if market_data.empty:
            log.error("Market data is empty. Cannot determine simulation dates. Run 'scripts/collect_data.py'.")
            return

        # Get the min and max dates available in the CSV
        available_dates = sorted(market_data['Date'].unique())
        start_date = available_dates[0]
        end_date = available_dates[-1]
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        log.info(f"Simulation period determined from data: {start_date_str} to {end_date_str}")
        log.info(f"Total trading days available: {len(available_dates)}")

    except FileNotFoundError:
        log.error("Market data file not found. Run 'scripts/collect_data.py' first.")
        return
    except Exception as e:
        log.error(f"Error determining simulation dates: {e}", exc_info=True)
        return

    # --- MULTI-MODEL BACKTEST LOOP ---
    active_models = [m for m in config.OPENROUTER_MODELS if m.get('active')]
    
    if not active_models and config.LLM_PROVIDER == 'openrouter':
        log.warning("No active models found in config.yaml. Please set 'active: true' for at least one model.")
        return

    all_model_results = {}

    # If provider is NOT openrouter (e.g. gemini), run once as before
    if config.LLM_PROVIDER != 'openrouter':
        # Create a dummy config wrapper for consistency
        active_models = [{'alias': config.LLM_PROVIDER.capitalize(), 'provider': config.LLM_PROVIDER}]

    for model_cfg in active_models:
        model_name = model_cfg.get('alias', 'Unknown Model')
        log.info(f"=== Running Backtest for Model: {model_name} ===")
        
        history = run_backtest(
            start_date=start_date_str,
            end_date=end_date_str,
            model_config=model_cfg
        )
        
        if history:
            all_model_results[model_name] = history
        else:
            log.warning(f"Backtest failed or returned no history for {model_name}")

    log.info("--- Starting Performance Analysis ---")

    # Calculate metrics for each model
    for model_name, history in all_model_results.items():
        log.info(f"--- Metrics for {model_name} ---")
        metrics = calculate_metrics(history)
        for metric, value in metrics.items():
            log.info(f"- {metric}: {value}")

    baseline_history = []
    try:
        # We already loaded market_data, so we can reuse it or reload it.
        # Reloading to be safe and consistent with analysis logic.
        
        # Filter dates for baseline (should match the simulation exactly)
        simulation_dates_df = market_data[
            (market_data['Date'] >= start_date) & 
            (market_data['Date'] <= end_date)
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

    except Exception as e:
        log.error(f"An error occurred during analysis: {e}", exc_info=True)

    log.info("Generating performance plot...")
    log.info(f"Models to plot: {list(all_model_results.keys())}")
    plot_performance(all_model_results, baseline_history)
    log.info("Plot generated and displayed.")


if __name__ == "__main__":
    main()
