import sys
import os
import argparse
import json
from datetime import datetime
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import pandas as pd
from src.backtester import run_backtest
from src.analysis import plot_performance, create_buy_and_hold_baseline
from src.data_loader import load_market_data
from src.logger import log
import config

from src.metrics import total_return, max_drawdown, sharpe_ratio, win_rate, calmar_ratio, alpha_vs_benchmark

RESULTS_DIR = os.path.join(PROJECT_ROOT, "data", "results")

def _safe_filename(alias):
    return alias.replace(" ", "_").replace("/", "-").replace("^", "")

def _load_market_data_with_dates(exchange="BIST30"):
    market_data = load_market_data(exchange=exchange)
    market_data['Date'] = pd.to_datetime(market_data['Date'])
    available_dates = sorted(market_data['Date'].unique())
    start_date = available_dates[0].strftime('%Y-%m-%d')
    end_date = available_dates[-1].strftime('%Y-%m-%d')
    return market_data, start_date, end_date

def run_single_model(model_input, exchange="BIST30", start_date=None, end_date=None, initial_cash=None, trading_approach=None):
    # Apply configuration overrides
    if initial_cash is not None:
        config.INITIAL_CASH = initial_cash
        log.info(f"CLI Override: INITIAL_CASH set to {initial_cash:,.2f}")

    # Determine model config
    model_config = None
    alias = ""
    
    # Check if model_input is a string representing an integer (index)
    is_index = False
    try:
        model_idx = int(model_input)
        is_index = True
    except (ValueError, TypeError):
        pass

    if is_index:
        if model_idx >= len(config.OPENROUTER_MODELS):
            log.error(f"Model index {model_idx} out of range. {len(config.OPENROUTER_MODELS)} models defined.")
            return None
        model_config = config.OPENROUTER_MODELS[model_idx]
        alias = model_config['alias']
    else:
        # Treat as string model_name
        alias = model_input
        model_config = {
            "alias": alias,
            "model_name": alias
        }

    active_trading_approach = trading_approach or getattr(config, 'PROMPT_VERSION', 'Balanced')
    log.info(f"=== Running backtest on {exchange} for model: {alias} (Approach: {active_trading_approach}) ===")

    try:
        market_data, default_start_date, default_end_date = _load_market_data_with_dates(exchange=exchange)
        run_start = start_date or default_start_date
        run_end = end_date or default_end_date
    except Exception as e:
        log.error(f"Failed to load market data for exchange {exchange}: {e}")
        raise RuntimeError(
            f"Failed to load market data for exchange {exchange}: {e}. "
            f"Please verify your internet connection/VPN and run 'python scripts/collect_data.py' to download data."
        )

    # Run the backtest simulation
    res = run_backtest(
        start_date=run_start,
        end_date=run_end,
        model_config=model_config,
        return_details=True,
        exchange=exchange,
        trading_approach=active_trading_approach
    )

    if not res or not res.get("history"):
        log.error(f"No results for {alias}.")
        raise RuntimeError(
            f"Backtest returned no history for model '{alias}'. "
            f"This likely means no trading days were found in the selected date range "
            f"(start: {run_start}, end: {run_end}). "
            f"Please pick a date range with actual market data."
        )

    history = res["history"]
    detailed_history = res["detailed_history"]
    trades = res["trades"]

    # Calculate index buy-and-hold baseline
    index_ticker = "^NDX" if exchange == "NASDAQ" else "XU030.IS"
    simulation_dates = market_data[
        (market_data['Date'] >= pd.Timestamp(run_start)) &
        (market_data['Date'] <= pd.Timestamp(run_end))
    ]['Date'].unique()
    simulation_dates = sorted(simulation_dates)
    
    baseline_history = create_buy_and_hold_baseline(
        config.INITIAL_CASH, [index_ticker], market_data, simulation_dates
    )

    # Calculate financial metrics
    model_returns = pd.Series(history).pct_change().fillna(0)
    benchmark_returns = pd.Series(baseline_history).pct_change().fillna(0) if baseline_history else pd.Series()
    
    daily_pnls = pd.Series([h.get("daily_pnl", 0.0) for h in detailed_history])
    positions = pd.Series([h.get("position_type", "FLAT") for h in detailed_history])
    
    tot_ret = total_return(pd.Series(history), config.INITIAL_CASH)
    max_dd = max_drawdown(pd.Series(history))
    sharpe = sharpe_ratio(model_returns)
    wr = win_rate(daily_pnls, positions)
    calmar = calmar_ratio(tot_ret, max_dd)
    alpha = alpha_vs_benchmark(model_returns, benchmark_returns)
    
    # Keep Sortino for backward compatibility
    downside_returns = model_returns.copy()
    downside_returns[downside_returns > 0] = 0
    downside_std = downside_returns.std()
    sortino = 0.0
    if downside_std > 0:
        sortino = (model_returns.mean() * 252) / (downside_std * np.sqrt(252))
        
    metrics = {
        "Cumulative Return": f"{tot_ret:.2%}",
        "Max Drawdown": f"{max_dd:.2%}",
        "Sharpe Ratio": f"{sharpe:.4f}",
        "Win Rate": f"{wr:.2%}",
        "Calmar Ratio": f"{calmar:.4f}",
        "Alpha vs Benchmark": f"{alpha:.2%}",
        "Sortino Ratio": f"{sortino:.2f}"
    }
    log.info(f"[{alias}] Metrics: {metrics}")

    exchange_results_dir = os.path.join(RESULTS_DIR, exchange)
    os.makedirs(exchange_results_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    start_date_str = run_start.replace("-", "")
    end_date_str = run_end.replace("-", "")

    result = {
        "model_id": model_config['model_name'],
        "model_name": model_config['model_name'],
        "alias": alias,
        "trading_approach": active_trading_approach,
        "prompt_version": active_trading_approach,  # Write both keys for backward-compatibility with UI columns
        "exchange": exchange,
        "date_range": [run_start, run_end],
        "initial_capital": config.INITIAL_CASH,
        "timestamp": timestamp,
        "metrics": metrics,
        "history": history,
        "detailed_history": detailed_history,
        "trades": trades,
        "benchmark": {
            "history": baseline_history,
            "total_return": f"{((baseline_history[-1] - baseline_history[0]) / baseline_history[0]):.2%}" if baseline_history else "0.00%"
        }
    }

    # Save timestamped run file
    out_filename = f"{exchange}_{_safe_filename(alias)}_{active_trading_approach}_{start_date_str}_{end_date_str}.json"
    out_path = os.path.join(exchange_results_dir, out_filename)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    log.info(f"Results saved to {out_path}")

    # Save latest run file copy for easy lookup
    latest_path = os.path.join(exchange_results_dir, f"latest_{_safe_filename(alias)}.json")
    with open(latest_path, "w") as f:
        json.dump(result, f, indent=2)
    log.info(f"Latest run copy saved to {latest_path}")

    return result

def plot_all(exchange="BIST30"):
    log.info(f"=== Generating combined benchmark plot for {exchange} ===")

    try:
        market_data, start_date, end_date = _load_market_data_with_dates(exchange=exchange)
    except Exception as e:
        log.error(f"Failed to load market data: {e}")
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

    exchange_results_dir = os.path.join(RESULTS_DIR, exchange)
    if not os.path.exists(exchange_results_dir):
        log.error(f"No results found for {exchange}.")
        return

    model_results = []
    all_metrics = {}

    result_files = sorted([f for f in os.listdir(exchange_results_dir) if f.startswith("latest_") and f.endswith(".json")])
    if not result_files:
        log.error(f"No result files found in {exchange_results_dir}. Run with --model first.")
        return

    for fname in result_files:
        with open(os.path.join(exchange_results_dir, fname)) as f:
            r = json.load(f)
        model_results.append({"alias": r["alias"], "history": r["history"]})
        all_metrics[r["alias"]] = r["metrics"]
        log.info(f"Loaded: {r['alias']} — {r['metrics']}")

    # Buy & Hold baseline
    baseline_history = []
    try:
        simulation_dates = market_data[
            (market_data['Date'] >= pd.Timestamp(start_date)) &
            (market_data['Date'] <= pd.Timestamp(end_date))
        ]['Date'].unique()
        simulation_dates = sorted(simulation_dates)
        
        index_ticker = "^NDX" if exchange == "NASDAQ" else "XU030.IS"
        baseline_history = create_buy_and_hold_baseline(
            config.INITIAL_CASH, [index_ticker], market_data, simulation_dates
        )
        
        # Calculate benchmark returns to compute metrics
        benchmark_returns = pd.Series(baseline_history).pct_change().fillna(0) if baseline_history else pd.Series()
        tot_ret = total_return(pd.Series(baseline_history), config.INITIAL_CASH)
        max_dd = max_drawdown(pd.Series(baseline_history))
        sharpe = sharpe_ratio(benchmark_returns)
        
        baseline_metrics = {
            "Cumulative Return": f"{tot_ret:.2%}",
            "Max Drawdown": f"{max_dd:.2%}",
            "Sharpe Ratio": f"{sharpe:.4f}"
        }
        all_metrics["Buy & Hold"] = baseline_metrics
        log.info(f"[Buy & Hold] Metrics: {baseline_metrics}")
    except Exception as e:
        log.error(f"Error creating baseline: {e}")

    log.info("=== BENCHMARK RESULTS ===")
    for name, metrics in all_metrics.items():
        log.info(f"  {name}: {metrics}")

    plot_performance(model_results, baseline_history)
    log.info("Plot saved to logs/performance_plot.png")

def run_all_models(exchange="BIST30", trading_approach="Balanced"):
    """Runs all models sequentially (original behavior)."""
    for idx in range(len(config.OPENROUTER_MODELS)):
        run_single_model(str(idx), exchange=exchange, trading_approach=trading_approach)
    plot_all(exchange=exchange)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Exchange LLM Benchmark")
    parser.add_argument("--model", type=str, metavar="INDEX_OR_NAME",
                        help="Run backtest for a single model by index (0-based) or name (e.g. gpt-4o).")
    parser.add_argument("--exchange", type=str, default="BIST30", choices=["BIST30", "NASDAQ"],
                        help="Exchange to run backtest on (BIST30 or NASDAQ). Default: BIST30.")
    parser.add_argument("--start-date", type=str,
                        help="Custom start date for simulation (YYYY-MM-DD).")
    parser.add_argument("--end-date", type=str,
                        help="Custom end date for simulation (YYYY-MM-DD).")
    parser.add_argument("--cash", type=float,
                        help="Custom initial cash amount for simulation.")
    parser.add_argument("--trading-approach", type=str, default="Balanced",
                        help="Trading approach: Balanced (default), Aggressive, or Conservative.")
    parser.add_argument("--plot", action="store_true",
                        help="Load all saved results and generate the combined plot.")
    args = parser.parse_args()

    if args.plot:
        plot_all(exchange=args.exchange)
    elif args.model is not None:
        run_single_model(
            model_input=args.model,
            exchange=args.exchange,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_cash=args.cash,
            trading_approach=args.trading_approach
        )
    else:
        run_all_models(exchange=args.exchange, trading_approach=args.trading_approach)
