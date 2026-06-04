import os
import json
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.analysis import calculate_metrics

RESULTS_DIR = os.path.join(PROJECT_ROOT, "data", "results")

def main():
    print("Recalculating metrics for all existing result files...")
    for exchange in ["BIST30", "NASDAQ"]:
        exch_dir = os.path.join(RESULTS_DIR, exchange)
        if not os.path.exists(exch_dir):
            continue
        for fname in os.listdir(exch_dir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(exch_dir, fname)
            try:
                with open(fpath, "r") as f:
                    data = json.load(f)
                
                history = data.get("history")
                if not history and "detailed_history" in data:
                    history = [d["total_value"] for d in data["detailed_history"]]
                
                if history:
                    new_metrics = calculate_metrics(history)
                    if new_metrics:
                        data["metrics"] = new_metrics
                        with open(fpath, "w") as f:
                            json.dump(data, f, indent=2)
                        print(f"Updated {exchange}/{fname} with metrics: {new_metrics}")
                    else:
                        print(f"Failed to calculate metrics for {fname} (empty returns).")
                else:
                    print(f"No history found in {fname}.")
            except Exception as e:
                print(f"Error processing {fname}: {e}")

if __name__ == "__main__":
    main()
