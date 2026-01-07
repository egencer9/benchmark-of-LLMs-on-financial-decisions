import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.logger import log

def calculate_metrics(portfolio_history, risk_free_rate=0.02):
    # ... (Metric calculation logic remains the same)
    if not portfolio_history or len(portfolio_history) < 2:
        return {}
    
    returns = pd.Series(portfolio_history).pct_change().dropna()
    if returns.empty: return {}

    cumulative_return = (portfolio_history[-1] / portfolio_history[0]) - 1
    rolling_max = pd.Series(portfolio_history).cummax()
    daily_drawdown = pd.Series(portfolio_history) / rolling_max - 1.0
    max_drawdown = daily_drawdown.min()
    
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std()
    annualized_return = returns.mean() * 252
    
    sortino = (annualized_return - risk_free_rate) / downside_std * np.sqrt(252) if downside_std > 0 else np.inf

    return {
        "Cumulative Return": f"{cumulative_return:.2%}",
        "Max Drawdown": f"{max_drawdown:.2%}",
        "Sortino Ratio": f"{sortino:.2f}"
    }

def plot_performance(all_histories, baseline_history):
    """
    Plots multiple portfolio histories against a baseline.
    all_histories: { "Model Name": [100, 101, ...], ... }
    """
    if not all_histories:
        log.warning("No portfolio history to plot.")
        return

    log.info("Plotting multi-model performance...")
    plt.figure(figsize=(14, 8))
    
    # Plot each model
    for model_name, history in all_histories.items():
        plt.plot(history, label=model_name, linewidth=2)

    # Plot baseline
    if baseline_history:
        plt.plot(baseline_history, label="Buy and Hold (Baseline)", linestyle='--', color='black', linewidth=2, alpha=0.7)

    plt.title("LLM Trading Arena: Multi-Model Performance Comparison")
    plt.xlabel("Trading Days")
    plt.ylabel("Portfolio Value ($)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    plot_filename = "logs/performance_plot.png"
    plt.savefig(plot_filename)
    log.info(f"Performance plot saved to {plot_filename}")
    plt.close()

def create_buy_and_hold_baseline(initial_investment, tickers, market_data, simulation_dates):
    # ... (Same logic as before)
    if len(simulation_dates) == 0: return []
    
    investment_per_ticker = initial_investment / len(tickers)
    shares_to_buy = {}
    cash_spent = 0
    
    first_day = market_data[market_data['Date'] == simulation_dates[0]]
    for ticker in tickers:
        row = first_day[first_day['ticker'] == ticker]
        if not row.empty:
            price = row.iloc[0]['Close']
            if price > 0:
                shares = investment_per_ticker / price
                shares_to_buy[ticker] = shares
                cash_spent += shares * price
    
    remaining_cash = initial_investment - cash_spent
    history = []
    
    for date in simulation_dates:
        val = remaining_cash
        day_data = market_data[market_data['Date'] == date]
        for ticker, shares in shares_to_buy.items():
            row = day_data[day_data['ticker'] == ticker]
            if not row.empty:
                val += shares * row.iloc[0]['Close']
        history.append(val)
        
    return history
