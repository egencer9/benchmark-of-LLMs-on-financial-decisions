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

    start_date_str = SIMULATION_START_DATE.strftime('%Y-%m-%d')
    end_date_str = SIMULATION_END_DATE.strftime('%Y-%m-%d')

    # Run the backtest
    portfolio_history = run_backtest(
        start_date=start_date_str,
        end_date=end_date_str
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
    baseline_history = [] # Initialize baseline_history to an empty list
    try:
        market_data = load_market_data()
        
        market_data['Date'] = pd.to_datetime(market_data['Date'])
        simulation_dates_df = market_data[
            (market_data['Date'] >= pd.to_datetime(start_date_str)) & 
            (market_data['Date'] <= pd.to_datetime(end_date_str))
        ]
        simulation_dates = simulation_dates_df['Date'].unique()

        if len(simulation_dates) > 0:
            # --- FIX: Assign the result to the baseline_history variable ---
            baseline_history = create_buy_and_hold_baseline(INITIAL_CASH, market_data, TICKERS, simulation_dates)
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

    # 3. Plot Results
    # Now, baseline_history will correctly contain the data or be an empty list
    log.info("Generating performance plot...")
    plot_performance(portfolio_history, baseline_history)
    log.info("Plot generated and displayed.")


if __name__ == "__main__":
    main()
