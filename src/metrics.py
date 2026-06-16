import numpy as np
import pandas as pd

def sharpe_ratio(daily_returns_series, risk_free_rate=0.0):
    """
    Calculates Sharpe Ratio of daily returns.
    Input: pandas Series of daily returns.
    """
    std = daily_returns_series.std()
    if daily_returns_series.empty or len(daily_returns_series) < 2 or pd.isna(std) or std == 0:
        return float('nan')
    # Annualized Sharpe = (Mean Daily Return - RF Daily) / Std Daily * sqrt(252)
    daily_rf = risk_free_rate / 252
    excess_returns = daily_returns_series - daily_rf
    sharpe = (excess_returns.mean() / std) * np.sqrt(252)
    return round(float(sharpe), 4)

def max_drawdown(equity_curve_series):
    """
    Calculates the maximum drawdown from an equity curve series.
    Input: pandas Series of equity values.
    """
    if equity_curve_series.empty or len(equity_curve_series) < 2:
        return 0.0
    peak = equity_curve_series.cummax()
    drawdown = (equity_curve_series - peak) / peak
    return round(float(drawdown.min()), 4)

def win_rate(daily_pnl_series, position_type_series):
    """
    Calculates win rate on active trading days (days where position is not FLAT).
    """
    # Align and filter where position is not FLAT
    active_days = position_type_series != 'FLAT'
    active_pnl = daily_pnl_series[active_days]
    
    if active_pnl.empty:
        return 0.0
    
    wins = (active_pnl > 0).sum()
    rate = wins / len(active_pnl)
    return round(float(rate), 4)

def total_return(equity_curve_series, initial_capital):
    """
    Calculates cumulative total return.
    """
    if equity_curve_series.empty or initial_capital == 0:
        return 0.0
    final_equity = equity_curve_series.iloc[-1]
    ret = (final_equity - initial_capital) / initial_capital
    return round(float(ret), 4)

def calmar_ratio(total_return_value, max_drawdown_value):
    """
    Calculates Calmar Ratio (Total Return / Max Drawdown absolute value).
    """
    abs_dd = abs(max_drawdown_value)
    if abs_dd == 0:
        return 0.0
    return round(float(total_return_value / abs_dd), 4)

def alpha_vs_benchmark(model_daily_returns, benchmark_daily_returns):
    """
    Calculates annualized alpha vs a benchmark index.
    """
    if model_daily_returns.empty or benchmark_daily_returns.empty:
        return 0.0
    # Align index of both series
    common_idx = model_daily_returns.index.intersection(benchmark_daily_returns.index)
    if len(common_idx) == 0:
        return 0.0
    m_ret = model_daily_returns.loc[common_idx]
    b_ret = benchmark_daily_returns.loc[common_idx]
    
    mean_alpha = m_ret.mean() - b_ret.mean()
    annualized_alpha = mean_alpha * 252
    return round(float(annualized_alpha), 4)
