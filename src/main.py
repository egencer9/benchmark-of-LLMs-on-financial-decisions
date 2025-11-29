import pandas as pd
from datetime import datetime, timedelta
from backtester import run_backtest
from analysis import calculate_metrics, plot_performance, create_buy_and_hold_baseline
from data_loader import load_market_data
from logger import log

# --- Simulation Configuration ---
SIMULATION_END_DATE = datetime.now()
SIMULATION_START_DATE = SIMULATION_END_DATE - timedelta(days=20) # Use a shorter period for quick tests
INITIAL_CASH = 100000
TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"] # Must match tickers in collect_data.py

def main():
    """
    Main function to run the backtesting simulation and analysis.
    """
    log.info("--- Starting NASDAQ LLM Trader Simulation ---")

    # Run the backtest
    portfolio_history = run_backtest(
        start_date=SIMULATION_START_DATE.strftime('%Y-%m-%d'),
        end_date=SIMULATION_END_DATE.strftime('%Y-%m-%d')
    )

    if not portfolio_history:
        log.warning("Backtest did not produce any results. Exiting.")
        return

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
        simulation_dates = pd.to_datetime(market_data.index.unique())
        simulation_dates = simulation_dates[(simulation_dates >= pd.to_datetime(SIMULATION_START_DATE)) & (simulation_dates <= pd.to_datetime(SIMULATION_END_DATE))]

        baseline_history = create_buy_and_hold_baseline(INITIAL_CASH, market_data, TICKERS, simulation_dates)
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


if __name__ == "__main__":
    main()
