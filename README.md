# NASDAQ/BIST30 LLM Trader Benchmark

Simulation framework for benchmarking whether large language models can make profitable, risk-aware index futures decisions using local market/news data and a single paid LLM request per trading day.

The project is inspired by STOCKBENCH, but adapted for a cost-controlled workflow: data is collected offline, the prompt uses selected/trimmed local market and news context, the LLM receives one master prompt per day, and all model decisions are saved as structured JSON backtest results.

## What This Project Does

- Runs intraday futures-style backtests on `NASDAQ` and `BIST30`.
- Trades only the index contract proxy:
  - `NASDAQ`: Micro E-mini NASDAQ-100 style simulation using `^NDX`
  - `BIST30`: VIOP-style BIST30 simulation using `XU030.IS`
- Uses index/component prices, portfolio state, news context, and optional technical indicators.
- Supports multiple trading approaches:
  - `Balanced`
  - `Aggressive`
  - `Conservative`
  - `TechnicalAnalysis`
- Saves each run to `data/results/<EXCHANGE>/`.
- Provides a FastAPI backend and Vite/React dashboard for running, inspecting, comparing, and deleting backtests.

## Repository Layout

```text
.
├── config.py                         # Exchange lists, trading settings, env keys
├── config.yaml                       # OpenRouter model list
├── METHODOLOGY.md                    # Modeling assumptions and limitations
├── requirements.txt                  # Python dependencies
├── start.sh / stop.sh                # Start/stop API + frontend
├── scripts/
│   ├── collect_data.py               # Market/news data collector
│   ├── run_nasdaq_batch.py           # Multi-model NASDAQ batch runner
│   ├── run_nasdaq_technical_batch.py # TechnicalAnalysis-only NASDAQ batch runner
│   └── recalculate_metrics.py
├── src/
│   ├── api.py                        # FastAPI backend
│   ├── backtester.py                 # Simulation engine
│   ├── llm_agent.py                  # Prompt construction, LLM calls, parsing
│   ├── trading_approach.py           # Strategy/risk profiles
│   ├── technical_indicators.py       # RSI/SMA/MACD/Bollinger/regime score
│   ├── data_cache.py                 # Parquet-backed data cache
│   ├── data_loader.py
│   ├── metrics.py
│   └── main.py                       # CLI entry point
├── frontend/
│   └── src/                          # React dashboard
├── data/
│   ├── market_data_*.csv             # Local market datasets
│   ├── news_data_*.csv               # Local news datasets
│   ├── cache/                        # Parquet cache
│   └── results/                      # Backtest result JSONs
└── plots/
    └── generate_bist_plots.py
```

## Setup

Create and activate a Python environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Install frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

Create a `.env` file in the project root:

```bash
OPEN_ROUTER_KEY=...
NEWS_API_KEY=...
FINNHUB_API_KEY=...
GEMINI_API_KEY=...
OPENAI_API_KEY=...
```

The main production path currently uses `OPEN_ROUTER_KEY` because `config.py` sets:

```python
LLM_PROVIDER = "openrouter"
```

## Run the App

Start both backend and frontend:

```bash
bash start.sh
```

Open:

```text
http://localhost:5173
```

API runs on:

```text
http://localhost:8000
```

Stop services:

```bash
bash stop.sh
```

Logs:

```text
logs/api_server.log
logs/frontend.log
```

## Data Collection

Collect market and news data:

```bash
python3 scripts/collect_data.py
```

Outputs:

```text
data/market_data_BIST30.csv
data/news_data_BIST30.csv
data/market_data_NASDAQ.csv
data/news_data_NASDAQ.csv
```

The cache layer also stores/loads Parquet files under:

```text
data/cache/
```

NewsAPI free-tier historical limits still matter. For older windows, missing news may be unavoidable unless Finnhub or another historical source is available.

## CLI Backtests

Run one model by model index:

```bash
python3 src/main.py \
  --model 0 \
  --exchange NASDAQ \
  --start-date 2026-05-15 \
  --end-date 2026-06-12 \
  --cash 100000 \
  --trading-approach Balanced
```

Run another approach:

```bash
python3 src/main.py --model 0 --exchange BIST30 --trading-approach TechnicalAnalysis
```

If no model is provided, `src/main.py` runs all configured OpenRouter models for the selected exchange/approach.

## Trading Approaches

`src/trading_approach.py` defines the risk and prompting stance.

`Balanced`

- Moderate risk.
- Linear confidence-to-position sizing.
- HOLD when signals are mixed.

`Aggressive`

- Higher risk budget.
- More willing to take directional trades.
- Convex sizing favors larger positions at medium/high confidence.

`Conservative`

- Lower risk budget.
- Requires confidence `>= 55` to enter LONG/SHORT.
- Squared confidence sizing reduces exposure.
- Often produces flat `0.00%` runs if the model repeatedly chooses HOLD/FLAT. This is not necessarily an API failure.

`TechnicalAnalysis`

- Adds an index technical analysis block to the master prompt.
- Uses RSI, SMA20/SMA50, MACD, Bollinger %B, 1D/5D/10D momentum, and a composite technical regime score.
- Technicals are used as secondary confirmation, not as the primary signal.

## Batch Runs

NASDAQ all-model batch across `Aggressive`, `Balanced`, and `Conservative`:

```bash
python3 scripts/run_nasdaq_batch.py
```

NASDAQ TechnicalAnalysis-only batch:

```bash
python3 scripts/run_nasdaq_technical_batch.py
```

The technical batch supports environment overrides:

```bash
BATCH_EXCHANGE=NASDAQ \
BATCH_START_DATE=2026-05-15 \
BATCH_END_DATE=2026-06-12 \
BATCH_INITIAL_CASH=100000 \
python3 scripts/run_nasdaq_technical_batch.py
```

Batch logs are written under:

```text
logs/
```

## Results

Each run is saved as JSON:

```text
data/results/<EXCHANGE>/<EXCHANGE>_<MODEL_ALIAS>_<APPROACH>_<START>_<END>.json
```

Example:

```text
data/results/NASDAQ/NASDAQ_OpenAI_GPT-4o_Balanced_20260515_20260612.json
```

Each JSON contains:

- model identity
- exchange
- date range
- initial capital
- trading approach
- daily equity history
- detailed per-day portfolio records
- trades
- metrics
- buy-and-hold benchmark

Main metrics:

- Cumulative Return
- Max Drawdown
- Sharpe Ratio
- Win Rate
- Calmar Ratio
- Alpha vs Benchmark
- Sortino Ratio

## Dashboard Workflow

The frontend dashboard supports:

- Exchange switching between `NASDAQ` and `BIST30`
- Model and trading approach selection
- Backtest execution
- Live WebSocket logs
- Saved run history with pagination
- Multi-run equity chart comparison
- Run details and trade ledger inspection
- Local market/news exploration
- Result deletion

Comparison plots in the dashboard use stable run filenames as chart keys, so selected model curves remain valid when changing history pages.

## Plot Generation

Generated report plots are derived artifacts. They do not need to be committed unless a report submission explicitly requires images.

Project plotting script:

```bash
python3 plots/generate_bist_plots.py
```

Manual comparison plots used during analysis were intentionally written outside the project flow, for example under:

```text
/private/tmp/
```

## Testing and Validation

Python syntax checks:

```bash
python3 -m py_compile src/api.py
python3 -m py_compile scripts/run_nasdaq_technical_batch.py
```

Frontend build:

```bash
cd frontend
npm run build
```

Unit tests:

```bash
python3 -m unittest discover test
```

Note: `npm run lint` currently reports many pre-existing issues, including generated `.vite/deps` files and existing React hook lint findings. `npm run build` is the reliable frontend verification path in the current project state.

## Methodological Notes

See `METHODOLOGY.md` for full assumptions. Important points:

- The default mode is intraday: enter on open, force close on close.
- The project simulates index futures exposure; individual component news is context only.
- The system currently assumes zero commissions and zero slippage.
- Current constituent lists are static, so historical constituent context has survivorship bias.
- The traded index price itself is historical, so PnL price execution is not affected by constituent survivorship.
- In intraday mode, same-day news is excluded to reduce look-ahead bias.

## Git Hygiene

Recommended not to commit:

- `.env`
- `venv/`
- large generated plot folders
- temporary outputs under `/private/tmp`
- local logs unless needed for debugging

Result JSONs may be committed if they are part of the benchmark submission. Plot PNGs are usually better kept in the final report rather than stored as source-controlled artifacts.
