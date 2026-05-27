import sys
import os
import argparse
import json
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import pandas as pd
from src.backtester import run_backtest
from src.analysis import calculate_metrics, plot_performance, create_buy_and_hold_baseline
from src.data_loader import load_market_data
from src.logger import log
import config

RESULTS_DIR = os.path.join(PROJECT_ROOT, "data", "results")


def _safe_filename(alias):
    return alias.replace(" ", "_").replace("/", "-")


def _load_market_data_with_dates(exchange="BIST30"):
    market_data = load_market_data(exchange=exchange)
    market_data['Date'] = pd.to_datetime(market_data['Date'])
    available_dates = sorted(market_data['Date'].unique())
    start_date = available_dates[0].strftime('%Y-%m-%d')
    end_date = available_dates[-1].strftime('%Y-%m-%d')
    return market_data, start_date, end_date


def run_single_model(model_index, exchange="BIST30", dev_mode=None, start_date=None, end_date=None, initial_cash=None):
    if model_index >= len(config.OPENROUTER_MODELS):
        log.error(f"Model index {model_index} out of range. {len(config.OPENROUTER_MODELS)} models defined.")
        return None

    # Apply configuration overrides
    if dev_mode is not None:
        config.DEV_MODE = dev_mode
        log.info(f"CLI Override: DEV_MODE set to {dev_mode}")
    if initial_cash is not None:
        config.INITIAL_CASH = initial_cash
        log.info(f"CLI Override: INITIAL_CASH set to ₺{initial_cash:,.2f}")

    model_config = config.OPENROUTER_MODELS[model_index]
    alias = model_config['alias']
    log.info(f"=== Running backtest on {exchange} for model: {alias} ===")

    try:
        market_data, default_start_date, default_end_date = _load_market_data_with_dates(exchange=exchange)
        run_start = start_date or default_start_date
        run_end = end_date or default_end_date
    except Exception as e:
        log.error(f"Failed to load market data for exchange {exchange}: {e}")
        return None

    res = run_backtest(
        start_date=run_start,
        end_date=run_end,
        model_config=model_config,
        return_details=True,
        exchange=exchange
    )

    if not res or not res.get("history"):
        log.warning(f"No results for {alias}.")
        return None

    history = res["history"]
    detailed_history = res["detailed_history"]
    trades = res["trades"]

    metrics = calculate_metrics(history)
    log.info(f"[{alias}] Metrics: {metrics}")

    exchange_results_dir = os.path.join(RESULTS_DIR, exchange)
    os.makedirs(exchange_results_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    result = {
        "alias": alias,
        "model_name": model_config['model_name'],
        "exchange": exchange,
        "timestamp": timestamp,
        "metrics": metrics,
        "history": history,
        "detailed_history": detailed_history,
        "trades": trades
    }

    # Save timestamped run file
    out_path = os.path.join(exchange_results_dir, f"{_safe_filename(alias)}_{timestamp}.json")
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

    exchange_results_dir = os.path.join(RESULTS_DIR, exchange)
    if not os.path.exists(exchange_results_dir):
        log.error(f"No results found for {exchange}.")
        return

    model_results = []
    all_metrics = {}

    # Look for latest files
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
        tickers = config.EXCHANGES.get(exchange, {}).get("tickers", config.TICKERS)
        baseline_history = create_buy_and_hold_baseline(
            config.INITIAL_CASH, tickers, market_data, simulation_dates
        )
        baseline_metrics = calculate_metrics(baseline_history)
        all_metrics["Buy & Hold"] = baseline_metrics
        log.info(f"[Buy & Hold] Metrics: {baseline_metrics}")
    except Exception as e:
        log.error(f"Error creating baseline: {e}")

    log.info("=== BENCHMARK RESULTS ===")
    for name, metrics in all_metrics.items():
        log.info(f"  {name}: {metrics}")

    plot_performance(model_results, baseline_history)
    log.info("Plot saved to logs/performance_plot.png")


def run_all_models(exchange="BIST30", dev_mode=None):
    """Runs all models sequentially (original behavior)."""
    for idx in range(len(config.OPENROUTER_MODELS)):
        run_single_model(idx, exchange=exchange, dev_mode=dev_mode)
    plot_all(exchange=exchange)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Exchange LLM Benchmark")
    parser.add_argument("--model", type=int, metavar="INDEX",
                        help="Run backtest for a single model by index (0-based). See config.yaml for order.")
    parser.add_argument("--exchange", type=str, default="BIST30", choices=["BIST30", "NASDAQ"],
                        help="Exchange to run backtest on (BIST30 or NASDAQ). Default: BIST30.")
    parser.add_argument("--dev-mode", type=str, choices=["true", "false"],
                        help="Override DEV_MODE configuration. Default: keep config.py value.")
    parser.add_argument("--start-date", type=str,
                        help="Custom start date for simulation (YYYY-MM-DD).")
    parser.add_argument("--end-date", type=str,
                        help="Custom end date for simulation (YYYY-MM-DD).")
    parser.add_argument("--cash", type=float,
                        help="Custom initial cash amount for simulation.")
    parser.add_argument("--plot", action="store_true",
                        help="Load all saved results and generate the combined plot.")
    args = parser.parse_args()

    dev_override = None
    if args.dev_mode == "true":
        dev_override = True
    elif args.dev_mode == "false":
        dev_override = False

    if args.plot:
        plot_all(exchange=args.exchange)
    elif args.model is not None:
        run_single_model(
            model_index=args.model,
            exchange=args.exchange,
            dev_mode=dev_override,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_cash=args.cash
        )
    else:
        run_all_models(exchange=args.exchange, dev_mode=dev_override)
