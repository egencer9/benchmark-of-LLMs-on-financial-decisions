import os
import json
import sys

def validate_file(fpath):
    print(f"Validating file: {fpath}")
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Assert top-level keys
    required_keys = ["alias", "model_name", "exchange", "timestamp", "metrics", "history", "detailed_history", "trades"]
    for k in required_keys:
        assert k in data, f"Missing key: {k}"
        
    assert isinstance(data["alias"], str), "alias must be a string"
    assert isinstance(data["model_name"], str), "model_name must be a string"
    assert isinstance(data["exchange"], str), "exchange must be a string"
    assert isinstance(data["timestamp"], str), "timestamp must be a string"
    assert isinstance(data["metrics"], dict), "metrics must be a dict"
    assert isinstance(data["history"], list), "history must be a list"
    assert isinstance(data["detailed_history"], list), "detailed_history must be a list"
    assert isinstance(data["trades"], list), "trades must be a list"
    
    # Assert metrics structure
    metrics = data["metrics"]
    required_metrics = ["Cumulative Return", "Max Drawdown", "Sortino Ratio"]
    for m in required_metrics:
        assert m in metrics, f"Missing metric key: {m}"
        assert isinstance(metrics[m], str), f"Metric {m} must be a string"
        
    # Assert detailed_history elements
    for idx, day in enumerate(data["detailed_history"]):
        required_day_keys = ["date", "total_value", "cash", "holdings"]
        for k in required_day_keys:
            assert k in day, f"detailed_history[{idx}] missing key: {k}"
        assert isinstance(day["date"], str), f"detailed_history[{idx}]['date'] must be a string"
        assert isinstance(day["total_value"], (int, float)), f"detailed_history[{idx}]['total_value'] must be a number"
        assert isinstance(day["cash"], (int, float)), f"detailed_history[{idx}]['cash'] must be a number"
        assert isinstance(day["holdings"], dict), f"detailed_history[{idx}]['holdings'] must be a dict"
        
    # Assert trades elements
    for idx, trade in enumerate(data["trades"]):
        required_trade_keys = ["ticker", "decision", "price", "quantity", "value", "confidence", "reasoning"]
        for k in required_trade_keys:
            assert k in trade, f"trades[{idx}] missing key: {k}"
        assert isinstance(trade["ticker"], str), f"trades[{idx}]['ticker'] must be a string"
        assert isinstance(trade["decision"], str), f"trades[{idx}]['decision'] must be a string"
        assert isinstance(trade["price"], (int, float)), f"trades[{idx}]['price'] must be a number"
        assert isinstance(trade["quantity"], (int, float)), f"trades[{idx}]['quantity'] must be a number"
        assert isinstance(trade["value"], (int, float)), f"trades[{idx}]['value'] must be a number"
        assert isinstance(trade["confidence"], (int, float)), f"trades[{idx}]['confidence'] must be a number"
        assert isinstance(trade["reasoning"], str), f"trades[{idx}]['reasoning'] must be a string"
        
    print(f"File {fpath} is VALID according to the schema!")

def main():
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results_dir = os.path.join(PROJECT_ROOT, "data", "results")
    if not os.path.exists(results_dir):
        print("No results directory found.")
        sys.exit(1)
        
    files_validated = 0
    for root, dirs, files in os.walk(results_dir):
        for file in files:
            if file.endswith(".json"):
                fpath = os.path.join(root, file)
                try:
                    validate_file(fpath)
                    files_validated += 1
                except AssertionError as e:
                    print(f"SCHEMA VALIDATION FAILED for {file}: {e}")
                    sys.exit(1)
                    
    if files_validated == 0:
        print("No JSON results found to validate.")
        sys.exit(1)
        
    print(f"Validation successful! Validated {files_validated} result file(s).")
    
if __name__ == "__main__":
    main()
