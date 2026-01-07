import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.logger import log

def calculate_metrics(portfolio_history, risk_free_rate=0.02):
    """
    Calculates key performance metrics for the backtest.
    """
    if not portfolio_history or len(portfolio_history) < 2:
        log.warning("Portfolio history is too short to calculate metrics.")
        return {}

    log.info("Calculating performance metrics...")
    returns = pd.Series(portfolio_history).pct_change().dropna()
    if returns.empty:
        log.warning("No returns were generated, cannot calculate metrics.")
        return {}

    cumulative_return = (portfolio_history[-1] / portfolio_history[0]) - 1
    rolling_max = pd.Series(portfolio_history).cummax()
    daily_drawdown = pd.Series(portfolio_history) / rolling_max - 1.0
    max_drawdown = daily_drawdown.min()
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std()
    annualized_return = returns.mean() * 252

    if downside_std > 0:
        sortino_ratio = (annualized_return - (risk_free_rate / 252)) / downside_std * np.sqrt(252)
    else:
        sortino_ratio = np.inf
        log.warning("No downside deviation; Sortino Ratio is infinite.")

    metrics = {
        "Cumulative Return": f"{cumulative_return:.2%}",
        "Max Drawdown": f"{max_drawdown:.2%}",
        "Sortino Ratio": f"{sortino_ratio:.2f}"
    }
    log.info(f"Metrics calculated: {metrics}")
    return metrics

def plot_performance(portfolio_history, baseline_history):
    """
    Plots the portfolio value against a baseline.
    """
    if not portfolio_history:
        log.warning("Cannot plot empty portfolio history.")
        return

    log.info("Plotting portfolio performance against baseline.")
    plt.figure(figsize=(14, 7))
    plt.plot(portfolio_history, label="LLM Agent Portfolio", color='blue')
    if baseline_history:
        plt.plot(baseline_history, label="Buy and Hold Baseline", linestyle='--', color='orange')
    plt.title("Portfolio Performance vs. Buy and Hold")
    plt.xlabel("Trading Days")
    plt.ylabel("Portfolio Value ($)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plot_filename = "logs/performance_plot.png"
    plt.savefig(plot_filename)
    log.info(f"Performance plot saved to {plot_filename}")
    plt.close()

def create_buy_and_hold_baseline(initial_investment, tickers, market_data, simulation_dates):
    """
    Creates a baseline portfolio that buys and holds the target stocks.
    Correctly accounts for unspent cash if some stocks cannot be bought.
    """
    if len(simulation_dates) == 0:
        log.warning("Simulation dates are empty, cannot create baseline.")
        return []

    log.info("Creating Buy-and-Hold baseline...")
    investment_per_ticker = initial_investment / len(tickers)
    shares_to_buy = {}
    
    # Track how much cash is actually spent
    cash_spent = 0

    first_day_data = market_data[market_data['Date'] == simulation_dates[0]]
    if first_day_data.empty:
        log.error("No market data for the first simulation day. Cannot create baseline.")
        return []

    for ticker in tickers:
        ticker_data = first_day_data[first_day_data['ticker'] == ticker]
        if not ticker_data.empty:
            price = ticker_data['Close'].iloc[0]
            if price > 0:
                shares = investment_per_ticker / price
                shares_to_buy[ticker] = shares
                cash_spent += (shares * price)
                log.debug(f"Baseline: Buying {shares:.2f} shares of {ticker} at ${price:.2f}")
            else:
                log.warning(f"Initial price for {ticker} is zero. Cannot buy shares for baseline.")
        else:
            log.warning(f"No data found for {ticker} on start date. Keeping allocation as cash.")

    # Calculate remaining cash (uninvested capital)
    remaining_cash = initial_investment - cash_spent

    baseline_history = []
    for date in simulation_dates:
        # Start daily value with the uninvested cash
        daily_value = remaining_cash
        
        current_day_data = market_data[market_data['Date'] == date]
        for ticker, shares in shares_to_buy.items():
            ticker_data = current_day_data[current_day_data['ticker'] == ticker]
            if not ticker_data.empty:
                price = ticker_data['Close'].iloc[0]
                daily_value += shares * price
            else:
                # If no price for today, use the last known value (simplified) or 0
                # Ideally we should forward fill, but for now let's assume price didn't change drastically or just skip
                pass 
        
        baseline_history.append(daily_value)

    log.info("Buy-and-Hold baseline created successfully.")
    return baseline_history
