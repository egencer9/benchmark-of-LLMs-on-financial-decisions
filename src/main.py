import sys
import os
import argparse
import json

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


def _load_market_data_with_dates():
    market_data = load_market_data()
    market_data['Date'] = pd.to_datetime(market_data['Date'])
    available_dates = sorted(market_data['Date'].unique())
    start_date = available_dates[0].strftime('%Y-%m-%d')
    end_date = available_dates[-1].strftime('%Y-%m-%d')
    return market_data, start_date, end_date


def run_single_model(model_index):
    if model_index >= len(config.OPENROUTER_MODELS):
        log.error(f"Model index {model_index} out of range. {len(config.OPENROUTER_MODELS)} models defined.")
        return

    model_config = config.OPENROUTER_MODELS[model_index]
    alias = model_config['alias']
    log.info(f"=== Running backtest for: {alias} ===")

    try:
        market_data, start_date, end_date = _load_market_data_with_dates()
    except Exception as e:
        log.error(f"Failed to load market data: {e}")
        return

    history = run_backtest(start_date=start_date, end_date=end_date, model_config=model_config)

    if not history:
        log.warning(f"No results for {alias}.")
        return

    metrics = calculate_metrics(history)
    log.info(f"[{alias}] Metrics: {metrics}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    result = {"alias": alias, "model_name": model_config['model_name'], "history": history, "metrics": metrics}
    out_path = os.path.join(RESULTS_DIR, f"{_safe_filename(alias)}.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    log.info(f"Results saved to {out_path}")


def plot_all():
    log.info("=== Generating combined benchmark plot ===")

    try:
        market_data, start_date, end_date = _load_market_data_with_dates()
    except Exception as e:
        log.error(f"Failed to load market data: {e}")
        return

    # Load all saved model results
    model_results = []
    all_metrics = {}

    result_files = sorted([f for f in os.listdir(RESULTS_DIR) if f.endswith(".json")])
    if not result_files:
        log.error(f"No result files found in {RESULTS_DIR}. Run with --model first.")
        return

    for fname in result_files:
        with open(os.path.join(RESULTS_DIR, fname)) as f:
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
        baseline_history = create_buy_and_hold_baseline(
            config.INITIAL_CASH, config.TICKERS, market_data, simulation_dates
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


def run_all_models():
    """Runs all models sequentially (original behaviour)."""
    try:
        market_data, start_date, end_date = _load_market_data_with_dates()
    except Exception as e:
        log.error(f"Failed to load market data: {e}")
        return

    model_results = []
    all_metrics = {}
    os.makedirs(RESULTS_DIR, exist_ok=True)

    for model_config in config.OPENROUTER_MODELS:
        alias = model_config['alias']
        log.info(f"=== Running backtest for: {alias} ===")

        history = run_backtest(start_date=start_date, end_date=end_date, model_config=model_config)
        if not history:
            log.warning(f"No results for {alias}. Skipping.")
            continue

        metrics = calculate_metrics(history)
        log.info(f"[{alias}] Metrics: {metrics}")

        result = {"alias": alias, "model_name": model_config['model_name'], "history": history, "metrics": metrics}
        out_path = os.path.join(RESULTS_DIR, f"{_safe_filename(alias)}.json")
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)

        model_results.append({"alias": alias, "history": history})
        all_metrics[alias] = metrics

    # Baseline
    baseline_history = []
    try:
        simulation_dates = market_data[
            (market_data['Date'] >= pd.Timestamp(start_date)) &
            (market_data['Date'] <= pd.Timestamp(end_date))
        ]['Date'].unique()
        baseline_history = create_buy_and_hold_baseline(
            config.INITIAL_CASH, config.TICKERS, market_data, simulation_dates
        )
        baseline_metrics = calculate_metrics(baseline_history)
        all_metrics["Buy & Hold"] = baseline_metrics
    except Exception as e:
        log.error(f"Error creating baseline: {e}")

    log.info("=== BENCHMARK RESULTS ===")
    for name, metrics in all_metrics.items():
        log.info(f"  {name}: {metrics}")

    plot_performance(model_results, baseline_history)
    log.info("Plot saved to logs/performance_plot.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BIST30 LLM Benchmark")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--model", type=int, metavar="INDEX",
                       help="Run backtest for a single model by index (0-based). See config.yaml for order.")
    group.add_argument("--plot", action="store_true",
                       help="Load all saved results and generate the combined plot.")
    args = parser.parse_args()

    if args.model is not None:
        run_single_model(args.model)
    elif args.plot:
        plot_all()
    else:
        run_all_models()
