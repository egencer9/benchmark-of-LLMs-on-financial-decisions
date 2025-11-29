# AGENTS.md - Project Context & Directives

## 🤖 1. Identity & Mission
**Project Name:** NASDAQ-LLM-Trader (Cost-Optimized Replication of STOCKBENCH)
**Role:** You are an expert Financial Quant Developer and AI Architect.
**Objective:** Build a simulation system that evaluates if an LLM (Large Language Model) can act as a profitable trading agent in the **NASDAQ** market.
**Core Reference:** You have access to `paper.pdf` (STOCKBENCH). Use it to understand the theoretical framework (sequential decision making, contamination-free data), but **strictly follow the cost-optimization rules below**.

---

## ⚠️ 2. PRIME DIRECTIVES (CRITICAL CONSTRAINTS)
**You must strictly adhere to these rules to prevent budget explosion. Any deviation will result in failure.**

1.  **The "One-Request" Rule:** You are **NOT** allowed to make separate API calls for each stock. You must aggregate all daily data (portfolio + market + news for ALL target stocks) into **ONE SINGLE PROMPT per trading day**.
2.  **Token Economy (Local Summarization):** Do not send raw, lengthy news text to the paid LLM API. You must implement a local summarization step (using `transformers` / Hugging Face with a small model like `distilbart` or `Qwen2-0.5B`) to compress news before the API call.
3.  **Strict JSON Output:** The LLM must return a clean JSON object containing decisions for all target stocks in one response. No conversational filler.
4.  **Data Separation:** Keep the "Data Fetching" logic (scripts) separate from the "Backtesting Logic" (src).

---

## 🏗️ 3. Architecture & Pipeline

Your implementation must follow this strict 3-Stage Pipeline:

### Stage 1: Data Preparation (Offline - Cost: $0)
* **Script:** `scripts/collect_data.py`
* **Task:** Fetch historical OHLCV data (via `yfinance`) and News (via `NewsAPI` or `Finnhub`) for NASDAQ target stocks (e.g., AAPL, MSFT, NVDA, TSLA, AMZN).
* **Output:** Save raw data to `data/market_data.csv` and `data/news_data.csv`.

### Stage 2: The Simulation Loop (Main Logic)
* **Script:** `src/backtester.py` (Main Engine)
* **Process:** Iterate through each trading day in the simulation period.
    1.  **Load:** Read that day's data from local CSVs.
    2.  **Summarize:** Use the local model to summarize relevant news chunks (Cost: $0).
    3.  **Prompt:** Construct the **Master Prompt** containing:
        * Current Portfolio State (Cash/Holdings).
        * Market Data for all stocks (Price/PE).
        * Summarized News for all stocks.
    4.  **Call:** Send to Paid LLM API (Gemini/GPT). **(This is the ONLY cost - 1 call per day)**.
    5.  **Execute:** Parse JSON response -> Update Portfolio (Cash/Holdings).
    6.  **Record:** Save daily portfolio value.

### Stage 3: Analysis (Offline - Cost: $0)
* **Script:** `src/analysis.py`
* **Task:** Calculate Cumulative Return, Max Drawdown, and Sortino Ratio. Compare against a "Buy-and-Hold" baseline.

---

## 📂 4. Project Structure

Ensure your code respects this structure:

```text
/nasdaq_llm_trader/
├── 📄 paper.pdf              # Reference research paper
├── 📄 AGENTS.md              # This file
├── 📂 data/                  # CSV storage (Do not commit to git)
│   ├── market_data.csv
│   └── news_data.csv
├── 📂 scripts/
│   └── collect_data.py       # Data fetcher (runs once)
├── 📂 src/
│   ├── main.py               # Entry point
│   ├── data_loader.py        # Reads CSVs into Pandas
│   ├── llm_agent.py          # Handles Prompting & API Calls
│   ├── backtester.py         # Simulation Loop Logic
│   └── analysis.py           # Financial Metrics & Plotting
├── 📄 config.py              # API Keys (Gitignored)
└── 📄 requirements.txt       # Dependencies