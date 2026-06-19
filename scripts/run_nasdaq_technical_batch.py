"""
NASDAQ Technical Analysis Batch Runner.

Runs every configured OpenRouter model once, using only the TechnicalAnalysis
trading approach. Existing result files are skipped.
"""
import os
import re
import subprocess
import sys
from datetime import datetime

import yaml


# OpenRouter slugs known to fail with 404 in previous batch runs.
KNOWN_BROKEN_MODELS = {
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3.7-sonnet",
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
}

# Higher-capacity models first.
PRIORITY_KEYWORDS = [
    "claude-sonnet-4",
    "o3",
    "o1",
    "gpt-4o",
    "gemini-2.5",
    "deepseek-r1",
    "deepseek-chat",
    "llama-4",
    "qwen3",
]


def _safe_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-.]", "_", value)


def get_model_priority(model_name: str) -> int:
    model_lower = model_name.lower()
    for index, keyword in enumerate(PRIORITY_KEYWORDS):
        if keyword in model_lower:
            return index
    return len(PRIORITY_KEYWORDS)


def write_line(log_handle, text: str = ""):
    print(text, flush=True)
    log_handle.write(text + "\n")
    log_handle.flush()


def stream_process(cmd, cwd: str, log_handle) -> int:
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    if process.stdout is not None:
        for line in process.stdout:
            print(line, end="", flush=True)
            log_handle.write(line)
            log_handle.flush()

    return process.wait()


def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_path = os.path.join(root_dir, "config.yaml")

    with open(config_path, "r", encoding="utf-8") as config_file:
        yaml_config = yaml.safe_load(config_file)

    models = yaml_config.get("openrouter_models", [])
    model_items = []
    for index, model in enumerate(models):
        model_name = model["model_name"]
        if model_name in KNOWN_BROKEN_MODELS:
            print(f"SKIP known broken model: {model['alias']} ({model_name})")
            continue

        item = dict(model)
        item["original_index"] = index
        item["priority"] = get_model_priority(model_name)
        model_items.append(item)

    model_items.sort(key=lambda item: (item["priority"], item["alias"]))

    exchange = os.getenv("BATCH_EXCHANGE", "NASDAQ")
    start_date = os.getenv("BATCH_START_DATE", "2026-05-15")
    end_date = os.getenv("BATCH_END_DATE", "2026-06-12")
    initial_cash = os.getenv("BATCH_INITIAL_CASH", "100000")
    approach = "TechnicalAnalysis"

    start_str = start_date.replace("-", "")
    end_str = end_date.replace("-", "")

    results_dir = os.path.join(root_dir, "data", "results", exchange)
    logs_dir = os.path.join(root_dir, "logs")
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(logs_dir, f"nasdaq_technical_batch_{timestamp}.log")

    python_exec = os.path.join(root_dir, "venv", "bin", "python")
    if not os.path.exists(python_exec):
        python_exec = sys.executable

    runtime_broken: set[str] = set()
    total_runs = len(model_items)

    with open(log_path, "w", encoding="utf-8") as log_handle:
        write_line(log_handle, "")
        write_line(log_handle, "NASDAQ TechnicalAnalysis batch starting")
        write_line(log_handle, f"Exchange: {exchange}")
        write_line(log_handle, f"Date range: {start_date} -> {end_date}")
        write_line(log_handle, f"Initial cash: {initial_cash}")
        write_line(log_handle, f"Planned tests: {total_runs} models x {approach}")
        write_line(log_handle, f"Follow log: {log_path}")
        write_line(log_handle, "=" * 72)

        for run_number, model in enumerate(model_items, start=1):
            alias = model["alias"]
            model_idx = model["original_index"]
            model_name = model["model_name"]
            safe_alias = _safe_filename(alias)
            label = f"[{run_number}/{total_runs}] {alias} | {approach}"

            if model_name in runtime_broken:
                write_line(log_handle, f"{label} -> SKIP runtime broken model")
                continue

            out_file = f"{exchange}_{safe_alias}_{approach}_{start_str}_{end_str}.json"
            out_path = os.path.join(results_dir, out_file)
            if os.path.exists(out_path):
                write_line(log_handle, f"{label} -> SKIP existing result: {out_path}")
                continue

            write_line(log_handle, "")
            write_line(log_handle, f"{label} -> RUNNING")

            cmd = [
                python_exec,
                os.path.join(root_dir, "src", "main.py"),
                "--model",
                str(model_idx),
                "--exchange",
                exchange,
                "--start-date",
                start_date,
                "--end-date",
                end_date,
                "--cash",
                str(initial_cash),
                "--trading-approach",
                approach,
            ]

            return_code = stream_process(cmd, cwd=root_dir, log_handle=log_handle)

            if return_code != 0:
                if not os.path.exists(out_path):
                    write_line(
                        log_handle,
                        f"{label} -> FAILED exit={return_code}; no result file, model marked runtime broken",
                    )
                    runtime_broken.add(model_name)
                else:
                    write_line(log_handle, f"{label} -> WARNING exit={return_code}; result file exists")
            else:
                if os.path.exists(out_path):
                    write_line(log_handle, f"{label} -> OK: {out_path}")
                else:
                    write_line(log_handle, f"{label} -> NO RESULT FILE; model marked runtime broken")
                    runtime_broken.add(model_name)

            write_line(log_handle, "-" * 72)

        write_line(log_handle, "")
        write_line(log_handle, "TechnicalAnalysis batch finished")
        if runtime_broken:
            write_line(log_handle, f"Runtime broken models: {sorted(runtime_broken)}")
        write_line(log_handle, f"Results directory: {results_dir}")
        write_line(log_handle, f"Log file: {log_path}")


if __name__ == "__main__":
    main()
