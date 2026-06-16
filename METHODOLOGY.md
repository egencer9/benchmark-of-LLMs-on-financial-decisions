# Methodology & Modeling Assumptions

This document outlines the architectural assumptions, portfolio mechanics, and statistical limitations of the LLM Financial Trader Simulation.

---

## 1. Simulation Modes

The system supports two distinct execution profiles defined in `config.py` via the `INTRADAY_ONLY` parameter:

### A. Intraday Mode (`INTRADAY_ONLY = True`)
*   **Execution Cycle:** Positions are entered on the day's **Open** and forced liquidated (FLAT) on the day's **Close**.
*   **Overnight Carry:** No positions are carried across days. The portfolio always starts each trading day FLAT.
*   **Information Set:** The LLM receives the day's **Open price** and news from the lookback window up to (but excluding) the current day.
*   **PnL Realization:** Profit or loss is calculated at the close and fully realized back into free cash.

### B. Overnight Mode (`INTRADAY_ONLY = False`)
*   **Execution Cycle:** Positions are opened or adjusted at the day's **Close** and carried across days.
*   **Mark-to-Market (MTM):** Unresolved position values are marked-to-market daily. Daily variation margin is added to or subtracted from the cash balance.
*   **Information Set:** The LLM receives the day's **Close price** and news up to and including the current day.

---

## 2. Portfolio & Margin Mechanics

The simulation trades **micro/index futures contracts** (MNQ for NASDAQ and VIOP for BIST30). 

*   **Cash Representation:** In `backtester.py`, `portfolio.cash` represents **free cash** (net of posted margin).
*   **Margin Posted:** Required collateral to hold the active contract. Released back to free cash upon position exit (FLAT or reverse).
*   **Equity:** Represents the total account liquidation value (Free Cash + Posted Margin + Unrealized PnL).
*   **Buying Power:** In the prompt, the model is shown **Available Capital for Margin** representing `Free Cash + Posted Margin`. If the model decides to reverse a position (e.g. LONG to SHORT), the long position is closed first, releasing the posted margin to fund the new short position.

---

## 3. Known Methodological Limitations

### A. Survivorship Bias
*   **Description:** The constituent lists of BIST30 and NASDAQ configured in `config.py` are static and reflect the components as of the current date (2026).
*   **Impact:** When running historical backtests (e.g., for 2023 or 2024), the LLM receives news and price data for companies that survived and belong to the index today. This introduces a positive selection bias (survivorship bias) in the news signals.
*   **Unbiased PnL:** Note that the traded asset is the index contract itself (`XU030.IS` / `^NDX`), which uses the true historical index close. Therefore, the execution price and PnL calculation are entirely free from survivorship bias. Only the individual stock context is biased.

### B. Transaction Costs & Commissions
*   **Description:** The current benchmark model assumes zero transaction fees, commissions, and zero slippage.
*   **Impact:** In real-world trading, daily round-trips (100% daily turnover in intraday mode) are subject to significant drag from broker commissions, exchange fees, and bid-ask spreads. Actual returns would be lower than the backtested results.

### C. Look-Ahead Bias Prevention
*   **News Window:** News is strictly filtered by date. In intraday mode, news published on or after the current day is hidden. In overnight mode, news published after the current day is hidden.
*   **RSS Scraper Filtering:** RSS feeds are filtered during collection to discard any entry published outside the requested date range.
