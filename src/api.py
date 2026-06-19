import os
import sys
import json
import asyncio
import time
import re
from typing import Optional, List, Literal
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import config
from src.data_loader import load_market_data, load_news_data
from src.logger import log

app = FastAPI(title="LLM Financial Benchmark API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RESULTS_DIR = os.path.join(PROJECT_ROOT, "data", "results")


class RunParams(BaseModel):
    model_index: int
    exchange: str  # "BIST30" or "NASDAQ"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    cash: Optional[float] = None
    trading_approach: Optional[Literal["Balanced", "Aggressive", "Conservative", "TechnicalAnalysis"]] = "Balanced"


class BacktestManager:
    def __init__(self):
        self.status = "idle"  # "idle", "running", "finished", "failed"
        self.active_model = None
        self.active_exchange = None
        self.logs: List[str] = []
        self.progress = {
            "current_day": 0,
            "total_days": 0,
            "percent": 0.0
        }
        self.exit_code = None
        self.active_subprocess = None
        self.ws_clients = set()
        self.lock = asyncio.Lock()

    def reset(self):
        self.logs = []
        self.progress = {
            "current_day": 0,
            "total_days": 0,
            "percent": 0.0
        }
        self.exit_code = None
        self.status = "idle"
        self.active_model = None
        self.active_exchange = None
        self.active_subprocess = None


manager = BacktestManager()


def mask_api_key(key: Optional[str]) -> str:
    if not key:
        return "Not Set"
    if len(key) <= 8:
        return "********"
    return f"{key[:4]}****{key[-4:]}"


# --- Caching Layer for Market Data ---
# Stores { exchange_name: { "timestamp": float, "data": dict } }
market_data_cache = {}
CACHE_TTL = 3600  # 1 hour cache TTL


def get_market_data_cached(exchange: str):
    now = time.time()
    if exchange in market_data_cache:
        cache_entry = market_data_cache[exchange]
        if now - cache_entry["timestamp"] < CACHE_TTL:
            log.info(f"Returning cached market data for {exchange}")
            return cache_entry["data"]

    log.info(f"Cache miss for {exchange}. Reading CSV from disk...")
    try:
        df = load_market_data(exchange=exchange)
        df['Date'] = pd.to_datetime(df['Date'])
        latest_date = df['Date'].max()
        latest_df = df[df['Date'] == latest_date]

        prices = {}
        for _, row in latest_df.iterrows():
            prices[row['ticker']] = float(row['Close'])

        # Load news statistics
        news_df = load_news_data(exchange=exchange)
        news_counts = news_df['ticker'].value_counts().to_dict()

        tickers_info = []
        exch_config = config.EXCHANGES.get(exchange, {})
        for ticker in exch_config.get("tickers", []):
            company_name = exch_config.get("companies", {}).get(ticker, ticker)
            tickers_info.append({
                "ticker": ticker,
                "company_name": company_name,
                "price": prices.get(ticker, 0.0),
                "news_count": int(news_counts.get(ticker, 0))
            })

        data = {
            "latest_date": latest_date.strftime('%Y-%m-%d') if not pd.isnull(latest_date) else None,
            "tickers": tickers_info
        }

        market_data_cache[exchange] = {
            "timestamp": now,
            "data": data
        }
        return data
    except Exception as e:
        log.error(f"Error loading market data cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load market data: {str(e)}")


async def broadcast_ws(message: dict):
    if not manager.ws_clients:
        return
    disconnected = set()
    for client in manager.ws_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.add(client)
    for client in disconnected:
        manager.ws_clients.discard(client)


def parse_log_line_for_progress(line: str):
    # Match total days: "Starting backtest from 2026-04-27 to 2026-05-27 (20 trading days)"
    if "trading days" in line:
        m = re.search(r"\((\d+)\s+trading\s+days\)", line)
        if m:
            manager.progress["total_days"] = int(m.group(1))
            manager.progress["current_day"] = 0
            manager.progress["percent"] = 0.0

    # Match current trading day: "--- Trading Day: 2026-05-27 ---"
    if "--- Trading Day:" in line:
        manager.progress["current_day"] += 1
        if manager.progress["total_days"] > 0:
            pct = (manager.progress["current_day"] / manager.progress["total_days"]) * 100.0
            manager.progress["percent"] = round(min(pct, 100.0), 1)


async def run_backtest_subprocess(params: RunParams):
    cmd = [
        sys.executable,
        "-u",  # Unbuffered stdout
        os.path.join(PROJECT_ROOT, "src", "main.py"),
        "--model", str(params.model_index),
        "--exchange", params.exchange
    ]
    if params.start_date:
        cmd.extend(["--start-date", params.start_date])
    if params.end_date:
        cmd.extend(["--end-date", params.end_date])
    if params.cash:
        cmd.extend(["--cash", str(params.cash)])
    if params.trading_approach:
        cmd.extend(["--trading-approach", params.trading_approach])

    log.info(f"Spawning backtest process: {' '.join(cmd)}")

    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=PROJECT_ROOT,
            env=env
        )
        manager.active_subprocess = proc

        while True:
            line_bytes = await proc.stdout.readline()
            if not line_bytes:
                break
            line = line_bytes.decode('utf-8', errors='replace').strip()
            clean_line = line.replace('\r', '')

            # Append log and parse progress
            manager.logs.append(clean_line)
            parse_log_line_for_progress(clean_line)

            # Broadcast update
            await broadcast_ws({
                "type": "log",
                "message": clean_line,
                "progress": manager.progress
            })

        exit_code = await proc.wait()
        manager.exit_code = exit_code
        manager.status = "finished" if exit_code == 0 else "failed"

        await broadcast_ws({
            "type": "exit",
            "code": exit_code,
            "status": manager.status
        })

    except Exception as e:
        log.error(f"Error in backtest subprocess execution: {e}")
        manager.status = "failed"
        manager.logs.append(f"CRITICAL ERROR: {str(e)}")
        await broadcast_ws({
            "type": "exit",
            "code": -1,
            "status": "failed"
        })
    finally:
        manager.active_subprocess = None


# --- REST Routes ---

@app.get("/api/config")
def get_api_config():
    """Returns available models, exchanges and env key configurations."""
    return {
        "models": config.OPENROUTER_MODELS,
        "exchanges": {
            k: {
                "currency": v["currency"],
                "currency_symbol": v["currency_symbol"],
                "tickers_count": len(v["tickers"])
            } for k, v in config.EXCHANGES.items()
        },
        "api_keys": {
            "GEMINI_API_KEY": mask_api_key(os.getenv("GEMINI_API_KEY")),
            "NEWS_API_KEY": mask_api_key(os.getenv("NEWS_API_KEY")),
            "OPEN_ROUTER_KEY": mask_api_key(os.getenv("OPEN_ROUTER_KEY")),
            "FINNHUB_API_KEY": mask_api_key(os.getenv("FINNHUB_API_KEY")),
        }
    }


@app.post("/api/backtest/run")
async def trigger_backtest(params: RunParams):
    """Enforces single-run policy and triggers a subprocess backtest."""
    async with manager.lock:
        if manager.status == "running":
            raise HTTPException(
                status_code=409,
                detail="A backtest is already in progress. Please wait for it to complete."
            )

        manager.reset()
        manager.status = "running"
        manager.active_exchange = params.exchange
        manager.active_model = config.OPENROUTER_MODELS[params.model_index]["alias"]

        # Run process in background task
        asyncio.create_task(run_backtest_subprocess(params))
        return {
            "message": "Backtest initiated.",
            "model": manager.active_model,
            "exchange": manager.active_exchange
        }


@app.get("/api/backtest/history")
def get_backtest_history(
    exchange: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    model: Optional[str] = None
):
    """Returns paginated history of past runs metadata for the specified exchange."""
    exchange_dir = os.path.join(RESULTS_DIR, exchange)
    if not os.path.exists(exchange_dir):
        return {"runs": [], "total": 0, "page": page, "limit": limit}

    runs = []
    for fname in os.listdir(exchange_dir):
        if fname.startswith("latest_") or not fname.endswith(".json"):
            continue
        fpath = os.path.join(exchange_dir, fname)
        try:
            stat = os.stat(fpath)
            with open(fpath) as f:
                r = json.load(f)
                r_history = r.get("history", [])
                initial_cap = r.get("initial_capital") or 1000000.0
                final_cap = r_history[-1] if r_history else initial_cap
                pnl_val = final_cap - initial_cap
                runs.append({
                    "filename": fname,
                    "alias": r.get("alias"),
                    "model_name": r.get("model_name"),
                    "timestamp": r.get("timestamp"),
                    "metrics": r.get("metrics"),
                    "history_length": len(r_history),
                    "trades_count": len(r.get("trades", [])),
                    "created_at": stat.st_mtime,
                    "exchange": r.get("exchange"),
                    "initial_capital": initial_cap,
                    "final_capital": final_cap,
                    "pnl": pnl_val,
                    "date_range": r.get("date_range"),
                    "trading_approach": r.get("trading_approach") or r.get("prompt_version") or "v1",
                    "prompt_version": r.get("trading_approach") or r.get("prompt_version") or "v1"
                })
        except Exception as e:
            log.warning(f"Error parsing history file {fname}: {e}")

    # Sort descending by timestamp
    runs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    if model:
        runs = [r for r in runs if r["alias"].lower() == model.lower()]

    total = len(runs)
    start = (page - 1) * limit
    end = start + limit
    paginated = runs[start:end]

    return {
        "runs": paginated,
        "total": total,
        "page": page,
        "limit": limit
    }


@app.get("/api/results/{exchange}/{filename}")
def get_run_details(exchange: str, filename: str):
    """Loads and returns the full JSON details for a specific run."""
    # Prevent directory traversal
    safe_filename = os.path.basename(filename)
    fpath = os.path.join(RESULTS_DIR, exchange, safe_filename)

    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Result file not found.")

    try:
        with open(fpath) as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read result file: {str(e)}")


@app.delete("/api/results/{exchange}/{filename}")
def delete_run(exchange: str, filename: str):
    """Deletes a specific run file from the results directory."""
    safe_filename = os.path.basename(filename)
    fpath = os.path.join(RESULTS_DIR, exchange, safe_filename)

    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Result file not found.")

    try:
        os.remove(fpath)
        log.info(f"Deleted result file: {fpath}")
        return {"message": "Run deleted successfully."}
    except Exception as e:
        log.error(f"Failed to delete run file {fpath}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete run file: {str(e)}")


@app.get("/api/results/compare")
def compare_runs(runs: str, exchange: str):
    """Diffs / returns details of multiple backtest runs side-by-side."""
    filenames = [f.strip() for f in runs.split(",") if f.strip()]
    if not filenames:
        raise HTTPException(status_code=400, detail="Provide at least 1 run to compare.")

    results = []
    for fname in filenames:
        safe_fname = os.path.basename(fname)
        fpath = os.path.join(RESULTS_DIR, exchange, safe_fname)
        if not os.path.exists(fpath):
            raise HTTPException(status_code=404, detail=f"Run '{safe_fname}' not found.")
        try:
            with open(fpath) as f:
                r = json.load(f)
                r["filename"] = safe_fname
                results.append(r)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse '{safe_fname}': {str(e)}")

    return results


@app.get("/api/market-data")
def get_market_data(exchange: str):
    """Returns exchange stocks, names, prices and news count (cached)."""
    return get_market_data_cached(exchange)


@app.get("/api/cache-status")
def get_cache_status():
    """Returns the date ranges currently cached for each exchange (parquet cache)."""
    try:
        from src.data_cache import cache_status
        return cache_status()
    except Exception as e:
        log.warning(f"Cache status error: {e}")
        return {"status": "unavailable", "error": str(e)}


@app.get("/api/news")
def get_news(exchange: str, limit: int = 50):
    """Returns latest news articles for the exchange."""
    try:
        news_df = load_news_data(exchange=exchange)
        news_df = news_df.sort_values(by='publishedAt', ascending=False).head(limit)

        articles = []
        for _, row in news_df.iterrows():
            articles.append({
                "ticker": row['ticker'],
                "publishedAt": row['publishedAt'].strftime('%Y-%m-%d %H:%M') if hasattr(row['publishedAt'], 'strftime') else str(row['publishedAt']),
                "title": row.get('title', ''),
                "description": row.get('description', ''),
                "source": row.get('source', 'Unknown')
            })
        return articles
    except Exception as e:
        log.error(f"Error loading news data for API: {e}")
        return []


# --- WebSocket Stream Routing ---

@app.websocket("/api/backtest/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    manager.ws_clients.add(websocket)

    try:
        # Stream current state initially
        await websocket.send_json({
            "type": "init",
            "status": manager.status,
            "active_model": manager.active_model,
            "active_exchange": manager.active_exchange,
            "progress": manager.progress,
            "logs": manager.logs
        })

        while True:
            # Maintain connection and listen for control commands
            data = await websocket.receive_text()
            if data == "cancel":
                if manager.status == "running" and manager.active_subprocess:
                    log.info("Terminating running backtest subprocess via user WebSocket command...")
                    manager.active_subprocess.terminate()
                    manager.status = "failed"
                    manager.logs.append("--- BACKTEST TERMINATED BY USER ---")

                    await broadcast_ws({
                        "type": "log",
                        "message": "--- BACKTEST TERMINATED BY USER ---",
                        "progress": manager.progress
                    })
                    await broadcast_ws({
                        "type": "exit",
                        "code": -9,
                        "status": "failed"
                    })

    except WebSocketDisconnect:
        pass
    finally:
        manager.ws_clients.discard(websocket)


if __name__ == "__main__":
    import uvicorn
    log.info("Starting API server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
